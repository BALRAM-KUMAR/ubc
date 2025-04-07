# razorpay_services.py
import asyncio
from fastapi import APIRouter, Depends, HTTPException, status, Request
import razorpay
from core.config import Settings
from datetime import datetime

settings = Settings()

class RazorpayService:
    def __init__(self):
        self.client = razorpay.Client(
            auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
        )

    async def create_order(self, amount: int, currency: str = "INR", receipt: str = None):
        loop = asyncio.get_event_loop()
        order_data = {
            "amount": amount * 100,  # Convert to paise
            "currency": currency,
            "receipt": receipt or f"receipt_{datetime.now().timestamp()}",
            "payment_capture": 1
        }
        try:
            return await loop.run_in_executor(
                None, 
                lambda: self.client.order.create(order_data)
            )
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Razorpay API Error: {str(e)}"
            )

    async def verify_payment(self, razorpay_order_id, razorpay_payment_id, razorpay_signature):
        loop = asyncio.get_event_loop()
        try:
            return await loop.run_in_executor(
                None,
                lambda: self.client.utility.verify_payment_signature({
                    "razorpay_order_id": razorpay_order_id,
                    "razorpay_payment_id": razorpay_payment_id,
                    "razorpay_signature": razorpay_signature
                })
            )
        except Exception as e:
            raise HTTPException(
                status_code=400,
                detail=f"Payment verification failed: {str(e)}"
            )
        
    async def get_payment_details(self, razorpay_payment_id):
        loop = asyncio.get_event_loop()
        try:
            return await loop.run_in_executor(
                None,
                lambda: self.client.payment.fetch(razorpay_payment_id)
            )
        except Exception as e:
            raise HTTPException(
                status_code=400,
                detail=f"Error fetching payment details: {str(e)}"
            )
