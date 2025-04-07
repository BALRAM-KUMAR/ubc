import base64
from fastapi import HTTPException
from .vault_client import VaultClient  # Import VaultClient for token retrieval

class EncryptionService:
    def __init__(self):
        self.vault_client = VaultClient()

    def encrypt_data(self, tenant_id: str, role: str, plaintext: str):
        """Encrypt plaintext data using Vault's transit engine."""
        try:
            token = self.vault_client.get_vault_token(tenant_id, role)
            self.vault_client.client.token = token
            response = self.vault_client.client.secrets.transit.encrypt_data(
                name=f"{tenant_id}-transit",
                plaintext=base64.b64encode(plaintext.encode()).decode()
            )
            return response['data']['ciphertext']
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    def decrypt_data(self, tenant_id: str, role: str, ciphertext: str):
        """Decrypt encrypted data using Vault's transit engine."""
        try:
            token = self.vault_client.get_vault_token(tenant_id, role)
            self.vault_client.client.token = token
            response = self.vault_client.client.secrets.transit.decrypt_data(
                name=f"{tenant_id}-transit",
                ciphertext=ciphertext
            )
            return base64.b64decode(response['data']['plaintext']).decode()
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    def encrypt_file(self, tenant_id: str, role: str, file_path: str):
        """Encrypt a file's content using Vault."""
        try:
            with open(file_path, "rb") as f:
                plaintext = f.read()
            encrypted_text = self.encrypt_data(tenant_id, role, plaintext.decode())
            return encrypted_text
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    def decrypt_file(self, tenant_id: str, role: str, encrypted_text: str, output_path: str):
        """Decrypt an encrypted file's content and save it."""
        try:
            decrypted_text = self.decrypt_data(tenant_id, role, encrypted_text)
            with open(output_path, "wb") as f:
                f.write(decrypted_text.encode())
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
