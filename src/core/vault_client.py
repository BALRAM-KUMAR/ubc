import hvac
import os
from fastapi import HTTPException
from typing import List

# Vault Configuration (Read from environment variables)
VAULT_ADDR = os.getenv("VAULT_ADDR", "http://35.239.94.67:8200")
VAULT_TOKEN = os.getenv("VAULT_TOKEN","hvs.afRXhGgU351MpShcsLhUAN21")  # Secure method to fetch Vault token

if not VAULT_TOKEN:
    raise ValueError("Vault token is missing! Set VAULT_TOKEN as an environment variable.")

# Initialize Vault Client
client = hvac.Client(url=VAULT_ADDR, token=VAULT_TOKEN)

# Role-based Policies (Fixed paths to kv/data/)
ROLE_POLICIES = {
    "super_admin": """
        path "kv/data/tenants/{tenant_id}/*" {
            capabilities = ["create", "read", "update", "delete", "list"]
        }
        path "transit/encrypt/{tenant_id}-transit" {
            capabilities = ["update"]
        }
        path "transit/decrypt/{tenant_id}-transit" {
            capabilities = ["update"]
        }
    """,
    "clinic_admin": """
        path "kv/data/tenants/{tenant_id}/*" {
            capabilities = ["create", "read", "update", "delete", "list"]
        }
        path "transit/encrypt/{tenant_id}-transit" {
            capabilities = ["update"]
        }
        path "transit/decrypt/{tenant_id}-transit" {
            capabilities = ["update"]
        }
    """,
    "doctor": """
        path "kv/data/tenants/{tenant_id}/patients/*" {
            capabilities = ["read", "list"]
        }
        path "transit/decrypt/{tenant_id}-transit" {
            capabilities = ["update"]
        }

    """,
    "staff": """
        path "kv/data/tenants/{tenant_id}/appointments/*" {
            capabilities = ["read", "update"]
        }
    """,
    "patient": """
        path "kv/data/tenants/{tenant_id}/patients/{patient_id}" {
            capabilities = ["read"]
        }

        path "transit/decrypt/{tenant_id}-transit" {
            capabilities = ["update"]
        }

    """
}

class VaultClient:
    def __init__(self):
        self.client = client

    def create_vault_policy(self, tenant_id: str, role: str):
        """Create a Vault policy for a specific tenant and role."""
        if role not in ROLE_POLICIES:
            raise ValueError(f"Invalid role: {role}")

        policy_content = ROLE_POLICIES[role].replace("{tenant_id}", tenant_id)
        self.client.sys.create_or_update_policy(
            name=f"{role}-policy-{tenant_id}",
            policy=policy_content
        )

    def generate_token(self, tenant_id: str, role: str):
        """Generate a Vault token for a role under a tenant."""
        policy_name = f"{role}-policy-{tenant_id}"
        response = self.client.auth.token.create(
            policies=[policy_name],
            renewable=True,
            ttl="24h"
        )
        return response["auth"]["client_token"]

    def store_token_in_vault(self, tenant_id: str, role: str, token: str):
        """Store generated token securely in Vault under the correct KV v2 path."""
        path = f"kv/data/tenants/{tenant_id}/tokens/{role}"
        try:
            self.client.secrets.kv.v2.create_or_update_secret(
                mount_point="kv",  # Specify mount point explicitly
                path=f"tenants/{tenant_id}/tokens/{role}",
                secret={"token": token}
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error storing token in Vault: {str(e)}")

    def get_vault_token(self, tenant_id: str, role: str):
        """Retrieve a token from Vault for a specific tenant and role."""
        try:
            path = f"tenants/{tenant_id}/tokens/{role}"
            response = self.client.secrets.kv.v2.read_secret_version(
                mount_point="kv",
                path=path
            )
            return response["data"]["data"]["token"]
        except hvac.exceptions.InvalidPath:
            raise HTTPException(status_code=404, detail=f"Token not found for {role} in tenant {tenant_id}")
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    async def register_tenant(self, tenant_id: str, roles: List):
        """Register a new tenant and create Vault policies dynamically based on database roles."""
        try:
            # Step 1: Create a transit key
            self.create_transit_key(tenant_id)

            # Step 2: Create policies and tokens
            for role in roles:
                self.create_vault_policy(tenant_id, role.name)
                token = self.generate_token(tenant_id, role.name)
                self.store_token_in_vault(tenant_id, role.name, token)

            return {"message": f"Tenant {tenant_id} registered, transit key & policies created!"}
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

        
    def create_transit_key(self, tenant_id: str):
        """Create a transit key for a specific tenant."""
        key_name = f"{tenant_id}-transit"

        try:
            self.client.secrets.transit.create_key(
                name=key_name, 
                key_type="aes256-gcm96",  # Strong encryption type
                exportable=False,      # Prevent exporting the key
                allow_plaintext_backup=False
            )
            print(f"✅ Created transit key: {key_name}")

        except Exception as e:
            if "existing key named" in str(e):
                print(f"ℹ️ Transit key '{key_name}' already exists, skipping creation.")
            else:
                raise HTTPException(status_code=500, detail=f"Error creating transit key: {str(e)}")
            

    def rotate_transit_key(self, tenant_id: str):
        """Rotate the transit encryption key for a specific tenant."""
        key_name = f"{tenant_id}-transit"

        try:
            self.client.secrets.transit.rotate_key(name=key_name)
            print(f"🔄 Successfully rotated transit key: {key_name}")

        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error rotating transit key: {str(e)}")
