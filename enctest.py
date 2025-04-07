from src.core.vault_client import VaultClient
from src.core.encryption_service import EncryptionService
import asyncio
import os

# Initialize VaultClient and EncryptionService
vault_client = VaultClient()
encryption_service = EncryptionService()

# Define Role class to match expected structure
class Role:
    def __init__(self, name):
        self.name = name

# Sample test values
TENANT_ID = "55"
ROLES = [Role("super_admin"), Role("clinic_admin"), Role("doctor"), Role("staff"), Role("patient")]
TEST_ROLE = "super_admin"
PLAIN_TEXT = "Hello, this is a secret message!"
TEST_DIR = "test_files"
os.makedirs(TEST_DIR, exist_ok=True)  # Create directory if it doesn't exist

TEST_FILE = os.path.join(TEST_DIR, "test.txt")
ENCRYPTED_FILE = os.path.join(TEST_DIR, "encrypted.txt")
DECRYPTED_FILE = os.path.join(TEST_DIR, "decrypted.txt")


async def test_register_tenant():
    """Test registering a tenant and creating policies & tokens."""
    print("\n[TEST] Registering Tenant...")
    try:
        result = await vault_client.register_tenant(TENANT_ID, ROLES)
        print("✅ Register Result:", result)
    except Exception as e:
        print("❌ Error in registering tenant:", str(e))

def test_get_token():
    """Test retrieving a token from Vault."""
    print("\n[TEST] Getting Token for role:", TEST_ROLE)
    try:
        token = vault_client.get_vault_token(TENANT_ID, TEST_ROLE)
        print("✅ Vault Token:", token)
    except Exception as e:
        print("❌ Error retrieving token:", str(e))

def test_encrypt_decrypt_data():
    """Test encrypting and decrypting a string."""
    print("\n[TEST] Encrypting Data...")
    try:
        encrypted_text = encryption_service.encrypt_data(TENANT_ID, TEST_ROLE, PLAIN_TEXT)
        print("Encrypted Text:", encrypted_text)

        print("\n[TEST] Decrypting Data...")
        decrypted_text = encryption_service.decrypt_data(TENANT_ID, TEST_ROLE, encrypted_text)
        print("Decrypted Text:", decrypted_text)

        assert decrypted_text == PLAIN_TEXT, "❌ Decryption failed!"
        print("✅ Data encryption & decryption test passed.")
    except Exception as e:
        print("❌ Error in encryption/decryption:", str(e))

def test_encrypt_decrypt_file():
    """Test encrypting and decrypting a file."""
    try:
        # Write plain text to test file
        with open(TEST_FILE, "w", encoding="utf-8") as f:
            f.write(PLAIN_TEXT)

        print("\n[TEST] Encrypting File...")
        encrypted_text = encryption_service.encrypt_file(TENANT_ID, TEST_ROLE, TEST_FILE)

        # Save encrypted content as binary to avoid encoding issues
        with open(ENCRYPTED_FILE, "wb") as f:
            f.write(encrypted_text.encode())  # Store as binary

        print(f"✅ Encrypted file saved at: {ENCRYPTED_FILE}")

        print("\n[TEST] Decrypting File...")

        # Read the encrypted file content before decryption
        with open(ENCRYPTED_FILE, "rb") as f:
            encrypted_text = f.read().decode()  # Read as binary, then decode

        decrypted_text = encryption_service.decrypt_data(TENANT_ID, TEST_ROLE, encrypted_text)

        # Write decrypted text to a file
        with open(DECRYPTED_FILE, "w", encoding="utf-8") as f:
            f.write(decrypted_text)

        # Read back and verify
        with open(DECRYPTED_FILE, "r", encoding="utf-8") as f:
            decrypted_content = f.read()

        print("Decrypted File Content:", decrypted_content)
        assert decrypted_content == PLAIN_TEXT, "❌ File decryption failed!"
        print("✅ File encryption & decryption test passed.")

    except Exception as e:
        print("❌ Error in file encryption/decryption:", str(e))



if __name__ == "__main__":
    asyncio.run(test_register_tenant())  # Run async function properly
    test_get_token()
    test_encrypt_decrypt_data()
    test_encrypt_decrypt_file()
    print("\n✅ All tests completed successfully!")
