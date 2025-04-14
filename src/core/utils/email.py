# from core.config import settings
# from fastapi_mail import FastMail, MessageSchema, ConnectionConfig

# conf = ConnectionConfig(
#     MAIL_USERNAME=settings.MAIL_USERNAME,
#     MAIL_PASSWORD=settings.MAIL_PASSWORD,
#     MAIL_FROM=settings.MAIL_FROM,
#     MAIL_PORT=settings.MAIL_PORT,
#     MAIL_SERVER=settings.MAIL_SERVER,
#     MAIL_STARTTLS=True,
#     MAIL_SSL=False,
#     USE_CREDENTIALS=True
# )

# async def send_invitation_email(recipient_email: str, invitation_token: str):
#     fm = FastMail(conf)
#     message = MessageSchema(
#         subject="You have been invited to join our platform",
#         recipients=[recipient_email],
#         body=f"Please click the link below to complete your registration:\n"
#              f"{settings.FRONTEND_URL}/register?token={invitation_token}",
#         subtype="plain"
#     )
#     await fm.send_message(message)