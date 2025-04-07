import json
import asyncio
import os
from sqlalchemy.exc import IntegrityError
from sqlalchemy.future import select
from core.models.public import ComplianceImplemented, Plan
from core.dependencies import get_db

async def load_compliance_data():
    """Loads compliance JSON data and inserts it asynchronously into the database if not already present."""
    async for session in get_db():
        try:
            # Get the absolute path of compliance_data.json
            file_path = os.path.join(os.path.dirname(__file__), "compliance_data.json")

            # Read JSON file
            with open(file_path, "r", encoding="utf-8") as file:
                compliance_data = json.load(file)

            for item in compliance_data:
                # Check if the compliance entry already exists
                result = await session.execute(select(ComplianceImplemented).filter_by(name=item["name"]))
                existing_entry = result.scalars().first()

                if not existing_entry:
                    # Create a new ComplianceImplemented object
                    new_entry = ComplianceImplemented(
                        name=item["name"],
                        details=item["details"],
                        description=item["description"]
                    )
                    session.add(new_entry)

            # Commit the changes
            await session.commit()
            print("✅ Compliance data successfully inserted!")

        except Exception as e:
            await session.rollback()
            print(f"❌ Error inserting compliance data: {e}")
        
        finally:
            await session.close()


async def load_plans_data():
    """Loads plan JSON data and inserts it asynchronously into the database if not already present."""
    async for session in get_db():
        try:
            # Get the absolute path of plans.json
            file_path = os.path.join(os.path.dirname(__file__), "plans.json")

            # Read JSON file
            with open(file_path, "r", encoding="utf-8") as file:
                plans_data = json.load(file)

            for plan in plans_data:
                # Check if the plan already exists
                result = await session.execute(select(Plan).filter_by(name=plan["name"]))
                existing_plan = result.scalars().first()

                if not existing_plan:
                    # Create a new Plan object
                    new_plan = Plan(
                        name=plan["name"],
                        price=plan["price"],
                        features=plan["features"],
                        recommended=plan["recommended"]
                    )
                    session.add(new_plan)

            # Commit the changes
            await session.commit()
            print("✅ Plans data successfully inserted!")

        except IntegrityError:
            await session.rollback()
            print("⚠️ Plans already exist, skipping insertion.")
        except Exception as e:
            await session.rollback()
            print(f"❌ Error inserting plans data: {e}")

        finally:
            await session.close()
