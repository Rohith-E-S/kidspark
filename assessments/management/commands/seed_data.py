"""Idempotent seeder: 8 categories, 24 questions, demo users and demo data.

Run with::

    python manage.py seed_data

Safe to run repeatedly — every record is matched by a natural key
(category code, question order/text, username) and updated in place.
"""

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from accounts.models import ChildProfile
from analytics.services import generate_assessment_result
from assessments import palette
from assessments.models import (
    AssessmentSession,
    Category,
    Choice,
    Question,
    SessionResponse,
)

CATEGORIES = [
    {
        'code': 'LOGICAL',
        'name': 'Logical & Mathematical',
        'pillar': 'APTITUDE',
        'description': (
            'Pattern recognition, number puzzles and deductive reasoning — how a child '
            'breaks a problem into ordered steps and reaches a conclusion.'
        ),
    },
    {
        'code': 'VERBAL',
        'name': 'Verbal & Linguistic',
        'pillar': 'APTITUDE',
        'description': (
            'Vocabulary, reading comprehension and word associations — how precisely a '
            'child understands and uses language.'
        ),
    },
    {
        'code': 'SPATIAL',
        'name': 'Spatial & Visual',
        'pillar': 'APTITUDE',
        'description': (
            'Mental rotation, shape matching and visual memory — how a child pictures and '
            'manipulates objects in their mind.'
        ),
    },
    {
        'code': 'CRITICAL',
        'name': 'Critical & Analytical',
        'pillar': 'APTITUDE',
        'description': (
            'Cause and effect and everyday problem solving — how a child weighs evidence '
            'and predicts what happens next.'
        ),
    },
    {
        'code': 'STEM',
        'name': 'STEM & Discovery',
        'pillar': 'INTEREST',
        'description': (
            'Science experiments, coding, robotics and taking things apart to see how '
            'they work.'
        ),
    },
    {
        'code': 'ARTS',
        'name': 'Arts & Creative Expression',
        'pillar': 'INTEREST',
        'description': (
            'Drawing, music, storytelling and design — making something new and expressive.'
        ),
    },
    {
        'code': 'NATURE',
        'name': 'Nature & Outdoors',
        'pillar': 'INTEREST',
        'description': (
            'Animals, the environment, space and physical exploration of the world outside.'
        ),
    },
    {
        'code': 'SOCIAL',
        'name': 'Social & Leadership',
        'pillar': 'INTEREST',
        'description': (
            'Teamwork, helping others, organising games and communicating with a group.'
        ),
    },
]

# ---------------------------------------------------------------------------
# Questions. Each entry: text, visual_hint, difficulty_weight, and choices.
#
# Objective choices are (text, lucide_icon, is_correct, score_weight).
# Preference choices are (text, lucide_icon, score_weight) where the weight is
# the affinity: 10 = love it, 5 = sometimes, 0 = not for me.
#
# An empty icon string is deliberate: when the choice text *is* the answer
# (numbers, times) an icon would only add noise.
# ---------------------------------------------------------------------------

QUESTIONS = [
    # ---------------------------- APTITUDE ---------------------------------
    {
        'category': 'LOGICAL', 'type': 'OBJECTIVE', 'difficulty_weight': 1,
        'text': 'Which number finishes the pattern?',
        'visual_hint': '2, 4, 6, 8, ?',
        'choices': [
            ('9', '', False, 0),
            ('10', '', True, 10),
            ('11', '', False, 0),
            ('12', '', False, 0),
        ],
    },
    {
        'category': 'LOGICAL', 'type': 'OBJECTIVE', 'difficulty_weight': 2,
        'text': 'Ravi is taller than Sam. Sam is taller than Mia. Who is the shortest?',
        'visual_hint': 'Ravi  >  Sam  >  Mia',
        'choices': [
            ('Ravi', 'user', False, 0),
            ('Sam', 'user-round', False, 0),
            ('Mia', 'person-standing', True, 10),
            ('Cannot tell', 'circle-help', False, 0),
        ],
    },
    {
        'category': 'LOGICAL', 'type': 'OBJECTIVE', 'difficulty_weight': 3,
        'text': 'A train leaves at 9:15 and arrives after 2 hours 45 minutes. What time does it arrive?',
        'visual_hint': '9:15  +  2 h 45 m  =  ?',
        'choices': [
            ('11:45', '', False, 0),
            ('12:00', '', True, 10),
            ('12:15', '', False, 0),
            ('11:30', '', False, 0),
        ],
    },
    {
        'category': 'VERBAL', 'type': 'OBJECTIVE', 'difficulty_weight': 1,
        'text': 'Which word means the same as "happy"?',
        'visual_hint': 'happy  =  ?',
        'choices': [
            ('Joyful', 'smile', True, 10),
            ('Angry', 'angry', False, 0),
            ('Tired', 'bed', False, 0),
            ('Hungry', 'utensils', False, 0),
        ],
    },
    {
        'category': 'VERBAL', 'type': 'OBJECTIVE', 'difficulty_weight': 2,
        'text': 'Complete the sentence: "The tiny seed grew into a ______ tree."',
        'visual_hint': 'a tiny seed  →  a ______ tree',
        'choices': [
            ('mighty', 'trending-up', True, 10),
            ('hungry', 'utensils', False, 0),
            ('powdery', 'snowflake', False, 0),
            ('noisy', 'megaphone', False, 0),
        ],
    },
    {
        'category': 'VERBAL', 'type': 'OBJECTIVE', 'difficulty_weight': 3,
        'text': 'Read this: "Though the sky was grey, Meera packed a picnic." How did Meera feel about the plan?',
        'visual_hint': 'a grey sky  ·  a packed picnic',
        'choices': [
            ('Determined to enjoy it', 'target', True, 10),
            ('Angry about the weather', 'angry', False, 0),
            ('Confused about the day', 'circle-help', False, 0),
            ('Sleepy and bored', 'bed', False, 0),
        ],
    },
    {
        'category': 'SPATIAL', 'type': 'OBJECTIVE', 'difficulty_weight': 1,
        'text': 'Which shape has exactly four equal sides?',
        'visual_hint': 'four equal sides',
        'choices': [
            ('Square', 'square', True, 10),
            ('Triangle', 'triangle', False, 0),
            ('Circle', 'circle', False, 0),
            ('Star', 'star', False, 0),
        ],
    },
    {
        'category': 'SPATIAL', 'type': 'OBJECTIVE', 'difficulty_weight': 2,
        'text': 'If you fold a square in half and cut a triangle from the folded edge, what appears when you open it?',
        'visual_hint': 'fold in half  →  cut a triangle  →  open it',
        'choices': [
            ('A symmetrical diamond', 'diamond', True, 10),
            ('A single triangle', 'triangle', False, 0),
            ('A circle', 'circle', False, 0),
            ('A rectangle', 'rectangle-horizontal', False, 0),
        ],
    },
    {
        'category': 'SPATIAL', 'type': 'OBJECTIVE', 'difficulty_weight': 3,
        'text': 'A cube is painted on all faces, then cut into 8 equal smaller cubes. How many small cubes have no paint at all?',
        'visual_hint': '1 painted cube  →  8 small cubes',
        'choices': [
            ('0', '', True, 10),
            ('2', '', False, 0),
            ('4', '', False, 0),
            ('8', '', False, 0),
        ],
    },
    {
        'category': 'CRITICAL', 'type': 'OBJECTIVE', 'difficulty_weight': 1,
        'text': 'You leave an ice cube on a plate in the sun. What happens first?',
        'visual_hint': 'ice cube  +  sunshine',
        'choices': [
            ('It melts into water', 'droplet', True, 10),
            ('It turns into steam', 'cloud', False, 0),
            ('It gets bigger', 'arrow-up', False, 0),
            ('It freezes harder', 'snowflake', False, 0),
        ],
    },
    {
        'category': 'CRITICAL', 'type': 'OBJECTIVE', 'difficulty_weight': 2,
        'text': 'Your plant sits on the window ledge and leans towards the glass. Why?',
        'visual_hint': 'a plant on the window ledge',
        'choices': [
            ('It grows towards the light', 'sun', True, 10),
            ('It is running out of soil', 'sprout', False, 0),
            ('It is thirsty', 'droplet', False, 0),
            ('The pot moved', 'flower', False, 0),
        ],
    },
    {
        'category': 'CRITICAL', 'type': 'OBJECTIVE', 'difficulty_weight': 3,
        'text': 'Two shops sell the same toy. Shop A: ₹100 with 20% off. Shop B: ₹85 flat. Which is the better deal?',
        'visual_hint': 'Shop A  ₹100 − 20%      vs      Shop B  ₹85',
        'choices': [
            ('Shop A at ₹80', 'store', True, 10),
            ('Shop B at ₹85', 'receipt', False, 0),
            ('Both are equal', 'scale', False, 0),
            ('Cannot work it out', 'circle-help', False, 0),
        ],
    },
    # ---------------------------- INTEREST ---------------------------------
    {
        'category': 'STEM', 'type': 'PREFERENCE', 'difficulty_weight': 1,
        'text': 'A big box arrives at home with an old radio inside. What do you want to do most?',
        'visual_hint': 'a box  ·  an old radio',
        'choices': [
            ('Take it apart to see what is inside', 'wrench', 10),
            ('Use the box to make something new', 'package', 5),
            ('Leave it and go play outside', 'trees', 0),
        ],
    },
    {
        'category': 'STEM', 'type': 'PREFERENCE', 'difficulty_weight': 2,
        'text': 'Your class can pick one extra club. Which one sounds most fun?',
        'visual_hint': 'one extra club',
        'choices': [
            ('Science experiments and coding club', 'flask-conical', 10),
            ('Art and music club', 'palette', 5),
            ('Nature walks club', 'bird', 0),
        ],
    },
    {
        'category': 'STEM', 'type': 'PREFERENCE', 'difficulty_weight': 3,
        'text': 'A friend says a robot can never be creative. What is your first reaction?',
        'visual_hint': '"a robot can never be creative"',
        'choices': [
            ('Let us build one and test it ourselves', 'wrench', 10),
            ('I would write a story about it instead', 'book-open', 5),
            ('I would ask more people what they think', 'users', 0),
        ],
    },
    {
        'category': 'ARTS', 'type': 'PREFERENCE', 'difficulty_weight': 1,
        'text': 'You have a free afternoon and a big sheet of paper. What happens?',
        'visual_hint': 'a free afternoon  ·  a big sheet of paper',
        'choices': [
            ('I draw or paint a whole scene', 'paintbrush', 10),
            ('I write a story on it', 'pen-line', 5),
            ('I make a paper aeroplane and fly it', 'plane', 0),
        ],
    },
    {
        'category': 'ARTS', 'type': 'PREFERENCE', 'difficulty_weight': 2,
        'text': 'Your school is putting on a show. Which job would you pick?',
        'visual_hint': 'the school show needs one more helper',
        'choices': [
            ('Design the sets and costumes', 'palette', 10),
            ('Host and introduce the acts', 'mic', 5),
            ('Sort out the lights and sound', 'speaker', 0),
        ],
    },
    {
        'category': 'ARTS', 'type': 'PREFERENCE', 'difficulty_weight': 3,
        'text': 'How do you like to remember a really good day?',
        'visual_hint': 'a really good day',
        'choices': [
            ('Draw or illustrate it', 'paintbrush', 10),
            ('Write a song or a poem about it', 'music-2', 5),
            ('Tell everyone the story aloud', 'megaphone', 0),
        ],
    },
    {
        'category': 'NATURE', 'type': 'PREFERENCE', 'difficulty_weight': 1,
        'text': 'You find a tiny snail on the path. What do you do?',
        'visual_hint': 'a tiny snail on the path',
        'choices': [
            ('Watch it closely and move it somewhere safe', 'snail', 10),
            ('Draw a picture of it later', 'pencil', 5),
            ('Show it to a friend straight away', 'hand', 0),
        ],
    },
    {
        'category': 'NATURE', 'type': 'PREFERENCE', 'difficulty_weight': 2,
        'text': 'Which weekend trip would you choose?',
        'visual_hint': 'pick a weekend trip',
        'choices': [
            ('A night under the stars tracking constellations', 'telescope', 10),
            ('A museum with dinosaur bones', 'bone', 5),
            ('A coding workshop', 'code', 0),
        ],
    },
    {
        'category': 'NATURE', 'type': 'PREFERENCE', 'difficulty_weight': 3,
        'text': 'Your local park is going to be partly rebuilt. What matters most to you?',
        'visual_hint': 'the park is being rebuilt',
        'choices': [
            ('Keeping the trees and ponds healthy', 'trees', 10),
            ('Adding a big open playground', 'blocks', 5),
            ('Adding a science discovery centre', 'microscope', 0),
        ],
    },
    {
        'category': 'SOCIAL', 'type': 'PREFERENCE', 'difficulty_weight': 1,
        'text': 'Two friends in your group are disagreeing. What do you do?',
        'visual_hint': 'two friends in your group disagree',
        'choices': [
            ('Help them talk it out', 'handshake', 10),
            ('Suggest a game we can all play', 'dice-5', 5),
            ('Give them space and keep playing', 'puzzle', 0),
        ],
    },
    {
        'category': 'SOCIAL', 'type': 'PREFERENCE', 'difficulty_weight': 2,
        'text': 'Your class is planning a small event. Which part suits you best?',
        'visual_hint': 'your class is planning a small event',
        'choices': [
            ('Leading the team and sharing the jobs', 'clipboard-list', 10),
            ('Making the posters and invites', 'image', 5),
            ('Working out the budget and timings', 'calculator', 0),
        ],
    },
    {
        'category': 'SOCIAL', 'type': 'PREFERENCE', 'difficulty_weight': 3,
        'text': 'A new student joins your class and sits alone. What is your move?',
        'visual_hint': 'a new student sits alone',
        'choices': [
            ('Invite them to join my group', 'user-plus', 10),
            ('Write them a friendly note', 'mail', 5),
            ('Tell the teacher about it', 'graduation-cap', 0),
        ],
    },
]

# ---------------------------------------------------------------------------
# Demo data
# ---------------------------------------------------------------------------

# Aarav: a confident logical thinker who loves STEM. The plan below is per
# category, one entry per question in that category's order (1, 2, 3), so the
# demo report shows a believable mix of Strong / Developing / Emerging bands
# instead of a flat wall of 100s and 0s.
AARAV_OBJECTIVE_PLAN = {
    'LOGICAL': [True, True, True],     # 100  strong
    'VERBAL': [True, False, True],     # 67   developing
    'SPATIAL': [True, True, False],    # 50   developing
    'CRITICAL': [False, True, True],   # 83   strong
}
AARAV_PREFERENCE_PLAN = {
    'STEM': [10, 10, 10],   # 100  strong
    'ARTS': [5, 0, 5],      # 33   emerging
    'NATURE': [5, 10, 5],   # 67   developing
    'SOCIAL': [10, 10, 5],  # 83   strong
}


class Command(BaseCommand):
    help = 'Seed KidSpark with categories, questions, demo users and demo data.'

    @transaction.atomic
    def handle(self, *args, **options):
        # Keep test runs and scripted calls quiet.
        if options.get('verbosity', 1) == 0:
            import io

            from django.core.management.base import OutputWrapper

            self.stdout = OutputWrapper(io.StringIO())

        self.stdout.write(self.style.MIGRATE_HEADING('Seeding KidSpark data...'))

        categories = self._seed_categories()
        self._seed_questions(categories)
        parent = self._seed_demo_user('demo_parent', 'demo1234', 'parent@kidspark.edu')
        self._seed_demo_user('admin', 'admin1234', 'admin@kidspark.edu', is_super=True)
        aarav = self._seed_child(parent, 'Aarav', 11, '6th Grade', 'indigo')
        diya = self._seed_child(parent, 'Diya', 8, '3rd Grade', 'rose')
        self._seed_completed_session(aarav)
        self._clear_sessions(diya)

        self.stdout.write(self.style.SUCCESS('\nKidSpark seed complete.'))
        self.stdout.write('  Demo parent : demo_parent / demo1234')
        self.stdout.write('  Superuser   : admin / admin1234')
        self.stdout.write('  Ready report: Aarav (age 11) - completed 24 questions')
        self.stdout.write('  Live trial  : Diya (age 8) - no sessions yet')

    # -- helpers ----------------------------------------------------------
    def _seed_categories(self):
        categories = {}
        for data in CATEGORIES:
            category, created = Category.objects.update_or_create(
                code=data['code'],
                defaults={
                    'name': data['name'],
                    'pillar': data['pillar'],
                    'description': data['description'],
                    # Icons come from the palette so the quiz, the dashboard and
                    # the report always agree on a dimension's symbol.
                    'icon_name': palette.category_icon(data['code']),
                },
            )
            categories[data['code']] = category
            state = 'created' if created else 'updated'
            self.stdout.write(f'  category {state}: {category.name}')
        return categories

    def _seed_questions(self, categories):
        counters = {code: 0 for code in categories}
        for entry in QUESTIONS:
            category = categories[entry['category']]
            counters[entry['category']] += 1
            order = counters[entry['category']]

            question, _ = Question.objects.update_or_create(
                category=category,
                order=order,
                question_type=entry['type'],
                defaults={
                    'text': entry['text'],
                    'visual_hint': entry.get('visual_hint', ''),
                    'difficulty_weight': entry['difficulty_weight'],
                    'age_group': 'ALL',
                },
            )

            # Rebuild choices so seeding stays idempotent even after edits.
            question.choices.all().delete()
            for choice_data in entry['choices']:
                if entry['type'] == 'OBJECTIVE':
                    text, icon, correct, weight = choice_data
                else:
                    # Preference choices carry affinity, never correctness.
                    text, icon, weight = choice_data
                    correct = False
                Choice.objects.create(
                    question=question,
                    text=text,
                    icon_name=icon,
                    is_correct=correct,
                    score_weight=weight,
                )

            label = 'objective' if entry['type'] == 'OBJECTIVE' else 'preference'
            self.stdout.write(f'  question: [{category.code}] {label} #{order}')

    def _seed_demo_user(self, username, password, email, is_super=False):
        user, created = User.objects.get_or_create(
            username=username,
            defaults={'email': email, 'is_staff': is_super, 'is_superuser': is_super},
        )
        user.email = email
        if is_super:
            user.is_staff = True
            user.is_superuser = True
        else:
            user.is_staff = True  # demo parent can peek at the admin
        user.set_password(password)
        user.save()

        state = 'created' if created else 'updated'
        self.stdout.write(f'  user {state}: {username}')
        return user

    def _seed_child(self, parent, name, age, grade, color):
        child, created = ChildProfile.objects.get_or_create(
            parent=parent,
            name=name,
            defaults={'age': age, 'grade': grade, 'avatar_color': color},
        )
        child.age = age
        child.grade = grade
        child.avatar_color = color
        child.save()
        state = 'created' if created else 'updated'
        self.stdout.write(
            f'  child {state}: {child.name} (age {child.age}, {child.age_group_label})'
        )
        return child

    def _clear_sessions(self, child):
        count = child.sessions.count()
        if count:
            child.sessions.all().delete()
            self.stdout.write(f'  cleared {count} session(s) for {child.name}')

    def _seed_completed_session(self, child):
        """Answer every question deterministically, then generate the result."""
        questions = list(
            Question.objects.for_age_group(child.age_group)
            .prefetch_related('choices')
            .order_by('order', 'id')
        )
        if not questions:
            self.stdout.write(self.style.WARNING('  no questions available to seed'))
            return

        session, _ = AssessmentSession.objects.get_or_create(
            child=child,
            is_completed=True,
            defaults={'current_question_index': len(questions)},
        )
        session.responses.all().delete()

        for index, question in enumerate(questions):
            choices = list(question.choices.all())
            code = question.category.code
            order = question.order

            if question.is_objective:
                plan = AARAV_OBJECTIVE_PLAN.get(code, [])
                wanted_correct = plan[order - 1] if len(plan) >= order else True
                pool = [c for c in choices if c.is_correct == wanted_correct]
            else:
                plan = AARAV_PREFERENCE_PLAN.get(code, [])
                target = plan[order - 1] if len(plan) >= order else 5
                pool = [c for c in choices if c.score_weight == target]
                if not pool:
                    pool = [c for c in choices if c.score_weight == 5]
            choice = (pool or choices)[0]

            SessionResponse.objects.create(
                session=session,
                question=question,
                selected_choice=choice,
                time_taken_seconds=8 + (index % 7),
            )

        session.is_completed = True
        session.completed_at = timezone.now()
        session.current_question_index = len(questions)
        session.save()

        result = generate_assessment_result(session)
        self.stdout.write(
            f'  session: {child.name} answered {len(questions)} questions'
        )
        self.stdout.write(
            f'  result: {result.persona_title} '
            f'(aptitude {result.overall_aptitude_percentage}%)'
        )
