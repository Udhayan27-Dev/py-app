from django.core.management.base import BaseCommand
from faq.models import FAQ, ErrorCode

class Command(BaseCommand):
    help = 'Seeds initial FAQs and ErrorCodes into the database'

    def handle(self, *args, **options):
        self.stdout.write("Seeding FAQs...")
        faqs_data = [
            {
                "question": "How is the study plan calculated?",
                "category": "planning",
                "answer": "PlanMyStudy calculates your schedule by analyzing your total days until exam day minus the final 2 dedicated revision days. Each subject is weighted by difficulty: Hard subjects receive triple weight (3x), Medium subjects double weight (2x), and Easy subjects single weight (1x). Available daily hours are distributed proportionally so challenging subjects get the deep focus they require."
            },
            {
                "question": "How do I change my exam date?",
                "category": "planning",
                "answer": "You can generate a new plan at any time with an updated exam date from the Plan Generator page. If you are signed in, you can keep multiple plans for different exams or replace your previous plan from the My Plans dashboard."
            },
            {
                "question": "How many hours per day is ideal for studying?",
                "category": "planning",
                "answer": "For most students, 3 to 6 focused hours per day is optimal. Studying for more than 6-7 hours without breaks often leads to cognitive fatigue and diminishing returns. PlanMyStudy recommends splitting your daily hours into 45-50 minute blocks using the Pomodoro technique."
            },
            {
                "question": "What is the Pomodoro technique?",
                "category": "techniques",
                "answer": "The Pomodoro Technique is a time-management method where you study with 100% focus for 25 minutes, followed by a 5-minute break. After completing 4 sessions (Pomodoros), take a longer 15-30 minute break. This keeps mental energy high and prevents burnout."
            },
            {
                "question": "How do revision days work in the timetable?",
                "category": "planning",
                "answer": "The final 2 days before your exam date are automatically reserved strictly for comprehensive revision. Day (Exam - 2) is designed for full subject synthesis, practice tests, and weak-point review. Day (Exam - 1) focuses on light formula review, concept recall, mental preparation, and adequate sleep."
            },
            {
                "question": "Can I save or print my study plan?",
                "category": "planning",
                "answer": "Yes! Registered users have all generated plans automatically saved to their My Plans dashboard. You can also click the 'Print / Save PDF' button on any generated plan view to print or export a clean, printable PDF version directly from your browser."
            },
            {
                "question": "Is PlanMyStudy free to use?",
                "category": "general",
                "answer": "Yes, PlanMyStudy is 100% free to use! You can create study plans, consult the AI support assistant, read study technique guides, and manage your schedules without any cost or subscription."
            },
            {
                "question": "How should I prioritize hard subjects?",
                "category": "techniques",
                "answer": "Schedule your hardest subjects during your peak alertness window—typically first thing in the morning. Use active recall and self-testing rather than passive reading. PlanMyStudy automatically allocates a larger proportion of study slots to hard-rated subjects."
            },
            {
                "question": "What should I do if I fall behind on my schedule?",
                "category": "planning",
                "answer": "Don't panic! Missing a study block is normal. Avoid cramming everything into one weekend. Instead, generate an updated plan with your remaining days, or dedicate one upcoming catch-up session by temporarily reducing low-priority review."
            },
            {
                "question": "How do I study when preparing for multiple exams?",
                "category": "planning",
                "answer": "Add all your subjects into the generator with their respective difficulties. The generator interleaves subjects throughout the week so you retain knowledge across all topics simultaneously, rather than cramming one subject at the expense of others."
            },
            {
                "question": "How do I contact support?",
                "category": "general",
                "answer": "You can reach our team directly using the floating AI Chat Assistant widget on any page. If the assistant cannot answer your specific question, it will automatically generate a Support Ticket for our human staff to review."
            },
            {
                "question": "How is my data used and protected?",
                "category": "account",
                "answer": "PlanMyStudy respects your privacy. We only store your study plan parameters and account credentials securely. Passwords are encrypted using industry-standard hashing algorithms (never stored in plain text), and we never sell your data to third parties."
            },
            {
                "question": "How do I reset my account password?",
                "category": "account",
                "answer": "If you forgot your password or need to update it, you can contact support via the chat widget or reach out to a staff administrator to reset your credentials. When choosing a new password, ensure it is at least 8 characters long and not entirely numeric."
            },
            {
                "question": "Why do study plans need an account to be saved?",
                "category": "account",
                "answer": "While guests can freely generate plans tied to their current browser session, creating an account ensures your timetable is safely stored in our database so you can access, edit, and review your schedule from any device."
            }
        ]

        created_faqs = 0
        for item in faqs_data:
            obj, created = FAQ.objects.update_or_create(
                question=item["question"],
                defaults={
                    "answer": item["answer"],
                    "category": item["category"],
                    "is_active": True
                }
            )
            if created:
                created_faqs += 1

        self.stdout.write(self.style.SUCCESS(f"Seeded {len(faqs_data)} FAQs ({created_faqs} newly created)."))

        self.stdout.write("Seeding ErrorCodes...")
        error_codes_data = [
            {
                "code": "400",
                "title": "Bad Request",
                "explanation": "The server could not understand the request due to invalid syntax, missing parameters, or malformed data sent from your browser.",
                "suggested_fix": "Check the form inputs, verify dates and subject fields are correctly formatted, and try submitting again."
            },
            {
                "code": "401",
                "title": "Unauthorized",
                "explanation": "Authentication is required to access this resource or action. You are currently not signed in.",
                "suggested_fix": "Please log in to your account with your username and password, then retry accessing the page or feature."
            },
            {
                "code": "403",
                "title": "Forbidden",
                "explanation": "You do not have permission to view or modify this resource. For instance, you cannot view or delete another user's study plans or access the staff dashboard without staff permissions.",
                "suggested_fix": "Make sure you are logged in with the correct account that owns the resource. If you believe this is a mistake, contact an administrator."
            },
            {
                "code": "404",
                "title": "Page Not Found",
                "explanation": "The requested URL or resource does not exist on the server. The link might be broken or the study plan was deleted.",
                "suggested_fix": "Double-check the web address or navigate back to the homepage or My Plans dashboard."
            },
            {
                "code": "429",
                "title": "Too Many Requests",
                "explanation": "You have submitted too many requests in a short period and triggered our rate limiter (e.g., maximum 5 login attempts per minute, or 20 chat queries per minute).",
                "suggested_fix": "Wait 60 seconds before sending another message or attempting to log in again."
            },
            {
                "code": "500",
                "title": "Internal Server Error",
                "explanation": "The server encountered an unexpected condition that prevented it from fulfilling your request. An error log has been generated.",
                "suggested_fix": "Refresh the page in a moment. If the issue persists, click 'Ask the assistant' or contact our support team."
            },
            {
                "code": "503",
                "title": "Service Unavailable",
                "explanation": "The server is currently unable to handle the request due to temporary maintenance or downstream service degradation.",
                "suggested_fix": "Check our /health/ status page to see if all services (database, MongoDB, external APIs) are operational."
            },
            {
                "code": "SP-4221",
                "title": "Not enough days to build a study plan",
                "explanation": "The exam date entered is in the past, today, or provides fewer days than the required minimum (at least 3 full days: 1 study day + 2 reserved revision days) for the requested study hours.",
                "suggested_fix": "Please choose an exam date at least 3 days in the future to allow for meaningful study distribution and mandatory final revision."
            }
        ]

        created_codes = 0
        for item in error_codes_data:
            obj, created = ErrorCode.objects.update_or_create(
                code=item["code"],
                defaults={
                    "title": item["title"],
                    "explanation": item["explanation"],
                    "suggested_fix": item["suggested_fix"]
                }
            )
            if created:
                created_codes += 1

        self.stdout.write(self.style.SUCCESS(f"Seeded {len(error_codes_data)} ErrorCodes ({created_codes} newly created)."))
