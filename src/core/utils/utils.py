from sqlalchemy import event
from ..config import settings

def encrypt_field(field, key=settings.ENCRYPTION_KEY):
    return encrypt(field, key)

def decrypt_field(field, key=settings.ENCRYPTION_KEY):
    return decrypt(field, key)

@event.listens_for(Patient, 'before_insert')
def encrypt_sensitive_data(mapper, connection, target):
    if target.ssn:
        target.ssn = encrypt_field(target.ssn, settings.ENCRYPTION_KEY)
    if target.insurance_id:
        target.insurance_id = encrypt_field(target.insurance_id, settings.ENCRYPTION_KEY)