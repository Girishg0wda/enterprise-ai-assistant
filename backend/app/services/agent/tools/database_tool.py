import logging
from sqlalchemy.orm import Session
from app.database.database import SessionLocal
from app.models.user import User
from app.models.conversation import Conversation

logger = logging.getLogger(__name__)

class DatabaseTool:
    def __init__(self):
        self.name = "database_tool"
        self.description = (
            "Queries the internal transactional database structure. Use this to pull account statistics, "
            "count users, check user details, conversation metrics, or structured system parameters."
        )

    def execute(self, query_intent: str) -> str:
        """Translates basic data lookups into safe SQLAlchemy ORM execution calls."""
        db: Session = SessionLocal()
        try:
            intent = query_intent.lower().strip().replace("'", "").replace('"', "")
            logger.info(f"🗄️ [Database Tool] Analyzing operational data request intent: '{intent}'")
            
            # 🚀 ROBUST MATCHING LAYER (Catches plurals and flexible phrasing)
            is_explicit_user_count = any(
                k in intent for k in [
                    "total registered users count", 
                    "total registered user count", 
                    "user count", 
                    "registered users", 
                    "registered user"
                ]
            )
            
            # Fallback sub-string lists for flexible parsing 
            is_user_query = any(k in intent for k in ["user", "users", "member", "members", "account", "accounts", "profile", "profiles"])
            is_count_query = any(k in intent for k in ["count", "total", "number", "how many", "sum"])
            
            # Intent A: User Counts
            if is_explicit_user_count or (is_user_query and is_count_query):
                user_count = db.query(User).count()
                return f"Database Metric: Total registered platform users count is {user_count}."
            
            # Intent B: Conversation Metrics
            elif any(k in intent for k in ["conversation", "conversations", "chat", "chats", "thread", "threads", "message", "messages"]) and is_count_query:
                chat_count = db.query(Conversation).count()
                return f"Database Metric: Total active conversation threads count is {chat_count}."
                
            else:
                return (
                    f"Database Tool Result: The query intent mapping '{query_intent}' is not recognized or "
                    f"supported by explicit safety profiles."
                )
        except Exception as e:
            logger.error(f"Database Tool execution failed: {str(e)}")
            return f"Database Tool exception: {str(e)}"
        finally:
            db.close()