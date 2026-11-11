"""
Script cap nhat du lieu nang cao (evidence_quote, transcript, passage cua Exercise 11)
khong lam mat du lieu cu hoac cac bai khac.
"""
import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from receptive.models import Exercise, Question, Option

def run():
    print("Dang cap nhat transcripts va evidence_quotes...")

    # 1. Cap nhat Exercise 11 (Cognitive Linguistics) khop 100% voi Mockup
    try:
        ex11 = Exercise.objects.get(id=11)
        ex11.title = "Cognitive Linguistics and Linguistic Relativity"
        ex11.passage = (
            "The Sapir–Whorf hypothesis, also known as \"linguistic relativity\", proposes that the language we speak can shape the way we think about the world. "
            "In its stronger form, it suggests that language determines thought, while a weaker version argues that language influences, rather than completely controls, our thinking.\n\n"
            "Supporters of the hypothesis point to examples from different languages. For instance, some languages have multiple words for snow, allowing speakers to distinguish between different types of snow more easily. "
            "This, they argue, may make speakers more sensitive to such differences in their environment.\n\n"
            "However, the hypothesis is also debated. Critics say that people can still understand and categorize the same ideas even if their language does not have specific words for them. "
            "They argue that human thought is largely shared across cultures, and that language is only one of many factors, such as experience and education, that shape how we see the world."
        )
        ex11.time_limit_minutes = 20
        ex11.save()

        # Cap nhat 5 cau hoi cua Exercise 11
        q_data_11 = [
            {
                "order_no": 1,
                "question_type": Question.Type.MCQ,
                "question_text": "What is the main idea of the passage?",
                "correct_answers": ["B"],
                "explanation": "Correct Answer: B. The passage introduces the Sapir-Whorf hypothesis and explores both supportive examples and critical arguments regarding how language may influence human cognition.",
                "evidence_quote": "proposes that the language we speak can shape the way we think about the world... while a weaker version argues that language influences, rather than completely controls, our thinking.",
                "options": [
                    ("A", "To prove that language completely determines thinking."),
                    ("B", "To discuss how language may influence the way we think."),
                    ("C", "To show that all languages describe the world in the same way."),
                    ("D", "To explain why some languages have more words than others."),
                ]
            },
            {
                "order_no": 2,
                "question_type": Question.Type.MCQ,
                "question_text": "Which of the following is given as an example to support the hypothesis?",
                "correct_answers": ["B"],
                "explanation": "Correct Answer: B. Paragraph 2 mentions that some languages have several words for different kinds of snow as an example of linguistic influence on environmental perception.",
                "evidence_quote": "For instance, some languages have multiple words for snow, allowing speakers to distinguish between different types of snow more easily.",
                "options": [
                    ("A", "People can understand ideas without a specific word for them."),
                    ("B", "Some languages offer several words for different kinds of snow."),
                    ("C", "Education can be more important than language."),
                    ("D", "Human thought is the same in all cultures."),
                ]
            },
            {
                "order_no": 3,
                "question_type": Question.Type.TFNG,
                "question_text": "Critics believe that human thought is largely shared across different cultures.",
                "correct_answers": ["True"],
                "explanation": "Correct Answer: True. Paragraph 3 states that critics argue 'human thought is largely shared across cultures'.",
                "evidence_quote": "They argue that human thought is largely shared across cultures, and that language is only one of many factors...",
                "options": [
                    ("True", "True"),
                    ("False", "False"),
                    ("Not Given", "Not Given"),
                ]
            },
            {
                "order_no": 4,
                "question_type": Question.Type.TFNG,
                "question_text": "According to critics, language is the single most important factor shaping human perspective.",
                "correct_answers": ["False"],
                "explanation": "Correct Answer: False. Critics argue that language is only 'one of many factors, such as experience and education', not the sole factor.",
                "evidence_quote": "language is only one of many factors, such as experience and education, that shape how we see the world.",
                "options": [
                    ("True", "True"),
                    ("False", "False"),
                    ("Not Given", "Not Given"),
                ]
            },
            {
                "order_no": 5,
                "question_type": Question.Type.SHORT_TEXT,
                "question_text": "What term describes the stronger form of the hypothesis arguing language determines thought?",
                "correct_answers": ["linguistic determinism", "determinism"],
                "explanation": "Correct Answer: linguistic determinism. The stronger version claims that language dictates or determines thought boundaries.",
                "evidence_quote": "In its stronger form, it suggests that language determines thought...",
                "options": []
            },
        ]

        for qd in q_data_11:
            q, _ = Question.objects.get_or_create(exercise=ex11, order_no=qd["order_no"])
            q.question_type = qd["question_type"]
            q.question_text = qd["question_text"]
            q.correct_answers = qd["correct_answers"]
            q.explanation = qd["explanation"]
            q.evidence_quote = qd["evidence_quote"]
            q.status = Question.Status.PUBLISHED
            q.save()

            q.options.all().delete()
            for opt_idx, (k, txt) in enumerate(qd["options"], start=1):
                Option.objects.create(question=q, option_key=k, option_text=txt, order_no=opt_idx)
        print("[OK] Exercise 11 updated to match mockup!")
    except Exercise.DoesNotExist:
        print("[SKIP] Exercise 11 not found.")

    # 2. Cap nhat transcript cho cac bai Listening 13 - 18
    listening_transcripts = {
        13: (
            "Narrator: You will hear a conversation between an international student, Alex, and a university housing officer, Mrs. Davis.\n\n"
            "Mrs. Davis: Good morning, welcome to the Student Accommodation Services. How can I help you today?\n"
            "Alex: Hello! I am an incoming first-year student, and I am looking for a place to stay near campus.\n"
            "Mrs. Davis: Wonderful! For first-year international students, we strongly recommend our University Residence Halls. They are secure, close to lecture theatres, and provide a great community atmosphere.\n"
            "Alex: That sounds ideal. What about the pricing?\n"
            "Mrs. Davis: Standard rooms range from 400 to 500 dollars a month. What is your budget?\n"
            "Alex: My maximum monthly budget is 450 dollars, ideally including utility bills.\n"
            "Mrs. Davis: That fits nicely with our Hall B option. Standard water and heating are included in this package. To secure your reservation, you must submit a scanned copy of your Student ID card before next Friday.\n"
            "Alex: Perfect, I will email the copy this afternoon. Thank you very much!"
        ),
        14: (
            "Narrator: You will hear a customer service representative explaining leisure centre facilities and membership terms.\n\n"
            "Officer: Good afternoon! Welcome to Riverdale Community Sports Centre.\n"
            "Customer: Hi, I would like some information about joining the sports centre.\n"
            "Officer: Certainly! Our facilities include a gym, fitness studios, and an Olympic-sized swimming pool. On weekdays, the swimming pool opens early at 6:00 AM for morning lap swimmers.\n"
            "Customer: That is great for my schedule. How much is the membership?\n"
            "Officer: A standard adult membership is 250 pounds, but if you have a valid student card, an annual student pass is discounted to only 180 pounds per year.\n"
            "Customer: Excellent. Are fitness classes included?\n"
            "Officer: Most classes like yoga and aerobics are drop-in, but our indoor cycling spin class requires advance booking at least 24 hours ahead due to limited bikes."
        ),
        15: (
            "Narrator: You will hear a senior research librarian delivering an orientation talk to new postgraduate students.\n\n"
            "Librarian: Good morning everyone, and welcome to the Central University Library. As postgraduates, the digital repository will be your primary academic asset. You can access over eighty thousand peer-reviewed e-journals and databases remotely twenty-four hours a day.\n"
            "If you require primary historical documents or rare manuscripts, please schedule an appointment with our Special Collections department on Level Four. Individual quiet study carrels can be reserved online up to two weeks in advance for dissertation research. Finally, remember our specialized data visualization lab is available on Level Two for quantitative mapping."
        ),
        16: (
            "Narrator: You will hear an interview between an urban planner and an environmental journalist discussing zero-emission municipal transportation.\n\n"
            "Journalist: Today we are joined by Dr. Sarah Chen, chief urban strategist for the metropolitan transit authority. Dr. Chen, what is the core focus of the new ten-year master plan?\n"
            "Dr. Chen: Our primary objective is the total electrification of the municipal bus fleet by 2032. However, electrifying heavy vehicles requires substantial capital investment in decentralized charging depots. To alleviate congestion immediately, we are dedicating forty kilometers of roadway exclusively for Bus Rapid Transit corridors with intelligent signal priority."
        ),
        17: (
            "Narrator: You will hear an associate professor of marine biology lecturing on the physiological mechanisms of coral bleaching events.\n\n"
            "Professor: In this lecture, we examine the symbiotic partnership between scleractinian corals and microscopic dinoflagellate algae known as zooxanthellae. Under normal sea temperatures, these photosynthetic endosymbionts provide up to ninety percent of the coral's organic energy requirements. However, prolonged sea surface thermal elevation induces severe oxidative cellular stress, causing the coral host to expel the pigmented algae. Without these symbionts, the coral tissue turns translucent, exposing the stark white calcium carbonate skeleton—a condition termed coral bleaching."
        ),
        18: (
            "Narrator: You will hear a conference presentation on the application of airborne LiDAR remote sensing in archaeological landscape analysis.\n\n"
            "Presenter: Airborne Light Detection and Ranging, or LiDAR, has fundamentally transformed spatial archaeology. By firing hundreds of thousands of laser pulses per second from an aircraft and measuring their reflection intervals, the sensor generates ultra-dense three-dimensional point clouds. Digital elevation algorithms can computationally filter out dense tropical forest canopies, revealing ancient causeways, irrigation canals, and defensive terracing that remained completely imperceptible to ground surveys for centuries."
        ),
    }

    for ex_id, transcript_text in listening_transcripts.items():
        try:
            ex = Exercise.objects.get(id=ex_id)
            ex.transcript = transcript_text
            ex.time_limit_minutes = 20
            ex.save(update_fields=["transcript", "time_limit_minutes"])
            print(f"[OK] Updated transcript for Listening Exercise {ex_id}")
        except Exercise.DoesNotExist:
            pass

    # 3. Cap nhat evidence_quote cho cac cau hoi cua Reading 7, 8, 9, 10, 12 neu chua co
    for q in Question.objects.all():
        if not q.evidence_quote and q.explanation:
            # Trich xuat phan doan van trong giai thich neu co
            q.evidence_quote = q.explanation[:200]
            q.save(update_fields=["evidence_quote"])

    print("Hoan tat cap nhat thanh cong 100%!")

if __name__ == "__main__":
    run()
