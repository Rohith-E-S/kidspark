"""Deterministic scoring + recommendation engine for KidSpark.

The whole module is intentionally rule-based: no randomness, no external calls.
Given a completed ``AssessmentSession`` it produces exactly one
``AssessmentResult`` (idempotent — re-running replaces the previous result).
"""

from collections import defaultdict

from assessments.models import Category
from analytics.models import AssessmentResult

APTITUDE_CODES = ['LOGICAL', 'VERBAL', 'SPATIAL', 'CRITICAL']
INTEREST_CODES = ['STEM', 'ARTS', 'NATURE', 'SOCIAL']

# --- Persona matrix -------------------------------------------------------
# (dominant_aptitude, dominant_interest) -> persona copy.
# Activities are keyed by age group so the roadmap always fits the child.
PERSONA_MATRIX = {
    ('LOGICAL', 'STEM'): {
        'title': 'The Young Architect & Code Explorer',
        'summary': (
            'Your child spots patterns and sequences faster than most, and they get real '
            'satisfaction from working out why something behaves the way it does. That '
            'logical engine pairs beautifully with an appetite for science and how-things-work '
            'discovery, so problems become puzzles rather than chores. Give them materials to '
            'build and break, and watch the reasoning compound.'
        ),
        'activities': {
            'JUNIOR': [
                'Build a 100-piece LEGO or magnetic-tile machine, then explain how each part moves.',
                'Solve three picture-pattern puzzles a day on a wipe-clean maths mat.',
                'Mix baking-soda and vinegar volcanoes and ask "what changed first?"',
                'Play ScratchJr to sequence a sprite through a 5-step obstacle course.',
            ],
            'MIDDLE': [
                'Build a Scratch game with scoring, lives and a win screen.',
                'Work through one chess puzzle set (mate in 2) three evenings a week.',
                'Try a LEGO Mindstorm or micro:bit line-follower build.',
                'Keep a "why did that happen?" science journal with a weekly experiment.',
            ],
            'SENIOR': [
                'Write a small Python program (quiz game or calculator) end to end.',
                'Enter an online algorithmic challenge and review the editorials afterwards.',
                'Build a working model of a simple machine and test its efficiency.',
                'Run a two-week data project: collect, chart and explain real observations.',
            ],
        },
        'domains': [
            'Robotics & Autonomous Systems',
            'Software Engineering & AI',
            'Data Science & Applied Mathematics',
            'Mechanical & Aerospace Engineering',
        ],
    },
    ('LOGICAL', 'ARTS'): {
        'title': 'The Pattern Composer',
        'summary': (
            'Your child reasons in structures: order, repetition, symmetry and rules come '
            'naturally to them. Placed next to a love of creative expression, that structure '
            'becomes rhythm, composition and design rather than cold calculation. They are the '
            'kind of thinker who can explain why a song or a picture simply works.'
        ),
        'activities': {
            'JUNIOR': [
                'Make repeating pattern art with stamps, then turn it into a paper quilt.',
                'Clap and copy rhythm patterns, then invent a new one of your own.',
                'Build symmetrical mandalas and fold-and-cut snowflakes.',
                'Storyboard a four-panel comic with a clear beginning, middle and end.',
            ],
            'MIDDLE': [
                'Compose a short melody in a free tool like Chrome Music Lab.',
                'Design a tessellating poster pattern using one shape.',
                'Write a choose-your-own-path story with branching logic.',
                'Learn simple perspective drawing and grid a photo.',
            ],
            'SENIOR': [
                'Produce a short animation where timing and pacing carry the story.',
                'Write and arrange an original piece in a DAW.',
                'Study golden-ratio composition and apply it to a design piece.',
                'Build an interactive story in Twine with real branching outcomes.',
            ],
        },
        'domains': [
            'Music Composition & Sound Design',
            'Game Design & Interactive Media',
            'Architecture & Structural Design',
            'Film Editing & Visual Effects',
        ],
    },
    ('LOGICAL', 'NATURE'): {
        'title': 'The Field Researcher',
        'summary': (
            'Your child brings a scientist\'s brain to everything: they categorise, compare and '
            'look for the rule underneath. That instinct finds its perfect subject in the living '
            'world, where patterns show up in leaf shapes, weather cycles and animal behaviour. '
            'They will happily spend an afternoon turning observations into conclusions.'
        ),
        'activities': {
            'JUNIOR': [
                'Start a pressed-leaf collection sorted by shape and edge type.',
                'Track the moon for a month on a wall chart.',
                'Sort rocks by weight, colour and texture, then label the groups.',
                'Plant two beans in different light and compare growth weekly.',
            ],
            'MIDDLE': [
                'Keep a nature journal with dated sketches and measurements.',
                'Log daily weather and look for patterns with the temperature chart.',
                'Identify ten local bird calls and record them.',
                'Build a small shadow-tracking sundial and mark the hours.',
            ],
            'SENIOR': [
                'Run a month-long biodiversity count in a fixed local plot.',
                'Analyse rainfall data and present it as a chart with a conclusion.',
                'Build a soil or water-quality test kit and track results.',
                'Model a simple ecosystem (predator/prey) in a spreadsheet.',
            ],
        },
        'domains': [
            'Environmental Science & Conservation',
            'Ecology & Field Biology',
            'Meteorology & Earth Sciences',
            'Agricultural Science & Sustainability',
        ],
    },
    ('LOGICAL', 'SOCIAL'): {
        'title': 'The Systems Strategist',
        'summary': (
            'Your child thinks in cause and effect, which makes them unusually good at seeing '
            'how a decision ripples through a group. Combined with a genuine pull towards people, '
            'that becomes fair rules, clear plans and calm problem-solving in a team. They are '
            'often the one who quietly reorganises the game so everybody can play.'
        ),
        'activities': {
            'JUNIOR': [
                'Invent a board game with three rules and teach it to the family.',
                'Take turns as "team captain" for a weekend chore plan.',
                'Solve "what would happen if..." fairness stories together.',
                'Run a mini scavenger hunt with clues you wrote yourself.',
            ],
            'MIDDLE': [
                'Organise a small class tournament and keep the score sheet.',
                'Debate one topic a week, taking the side you disagree with.',
                'Plan a group project timeline and assign the roles.',
                'Volunteer to run one activity at a community event.',
            ],
            'SENIOR': [
                'Chair a club meeting with an agenda you wrote.',
                'Run a short survey and present the findings to the group.',
                'Manage a team budget for a small event end to end.',
                'Write a code of conduct for a team you belong to.',
            ],
        },
        'domains': [
            'Law & Public Policy',
            'Management & Operations',
            'Economics & Strategy Consulting',
            'Civic Leadership & Diplomacy',
        ],
    },
    ('VERBAL', 'STEM'): {
        'title': 'The Science Communicator',
        'summary': (
            'Your child has a gift for language: they read quickly, remember words precisely and '
            'explain things well. Pair that with a fascination for how the world works and you get '
            'someone who can make a difficult idea feel obvious to everybody else. They will '
            'probably be the one presenting the group\'s findings.'
        ),
        'activities': {
            'JUNIOR': [
                'Read a science picture book, then explain it in your own words.',
                'Make a "word of the day" jar with one new science word added daily.',
                'Record a two-minute "kid explainer" video about the water cycle.',
                'Label a diagram of a plant or rocket and describe each part aloud.',
            ],
            'MIDDLE': [
                'Write a one-page illustrated explainer on a favourite invention.',
                'Keep a science vocabulary log with definitions in your own words.',
                'Give a five-minute talk on a discovery that changed the world.',
                'Start a mini podcast episode about a "why is the sky blue?" question.',
            ],
            'SENIOR': [
                'Write a 700-word popular-science article and get it edited.',
                'Learn to read a research abstract and summarise it in three sentences.',
                'Debate a technology-ethics topic with evidence on both sides.',
                'Script and record a ten-minute science explainer video.',
            ],
        },
        'domains': [
            'Science Journalism & Communication',
            'Technical Writing & Documentation',
            'Research Science & Academia',
            'Product Management for Deep Tech',
        ],
    },
    ('VERBAL', 'ARTS'): {
        'title': 'The Imaginative Storyteller',
        'summary': (
            'Your child lives in language: stories, wordplay, voices and characters come easily. '
            'Because they also love making things, those words turn into scripts, songs, comics '
            'and performances with real shape. Language is their instrument and imagination is '
            'the room they play it in.'
        ),
        'activities': {
            'JUNIOR': [
                'Write and illustrate a six-page picture book with a beginning and an end.',
                'Act out a favourite story with props and different voices.',
                'Make a "story jar" of characters and settings to pull out at bedtime.',
                'Turn a nursery rhyme into a brand-new adventure.',
            ],
            'MIDDLE': [
                'Write a 500-word short story and read it aloud to someone.',
                'Script a four-minute play for two friends to perform.',
                'Start a daily journal: three sentences, one new word each day.',
                'Turn a song you love into a short comic strip.',
            ],
            'SENIOR': [
                'Draft a 2,000-word short story and revise it twice.',
                'Write a one-act play and stage a table read.',
                'Enter a poetry or essay competition with an edited entry.',
                'Pitch and produce a short film from a script you wrote.',
            ],
        },
        'domains': [
            'Creative Writing & Publishing',
            'Theatre, Film & Screenwriting',
            'Advertising & Brand Narrative',
            'Journalism & Media Production',
        ],
    },
    ('VERBAL', 'NATURE'): {
        'title': 'The Nature Narrator',
        'summary': (
            'Your child notices detail and puts it into words: textures, colours, small changes '
            'in the weather and the way things grow. That verbal precision makes them a natural '
            'observer and recorder of the outdoor world. They do not just see nature — they '
            'describe it well enough for you to see it too.'
        ),
        'activities': {
            'JUNIOR': [
                'Keep a picture diary of the same tree across four seasons.',
                'Make up a story where an animal is the main character.',
                'Collect five leaves and describe each one in one sentence.',
                'Read a nature poem aloud outdoors and write your own.',
            ],
            'MIDDLE': [
                'Write weekly nature-journal entries with drawn detail.',
                'Listen to a bird call and describe it in words others can match.',
                'Write a letter from the perspective of a river or a tree.',
                'Start a small herbarium with captions for each specimen.',
            ],
            'SENIOR': [
                'Write a nature column for a school newsletter.',
                'Produce a photo essay with written captions on a local habitat.',
                'Research and present on one endangered species close to home.',
                'Interview a local environmentalist and publish the piece.',
            ],
        },
        'domains': [
            'Environmental Journalism',
            'Conservation & Field Research',
            'Museum Curation & Natural History',
            'Sustainable Tourism & Education',
        ],
    },
    ('VERBAL', 'SOCIAL'): {
        'title': 'The Voice of the Group',
        'summary': (
            'Your child is articulate, empathetic and quick to understand what someone is really '
            'saying. Putting that together with a strong pull towards people makes them a natural '
            'mediator, presenter and team anchor. They tend to be the one who makes sure everyone '
            'has been heard before a decision is made.'
        ),
        'activities': {
            'JUNIOR': [
                'Practise "one kind sentence" at dinner: say something you appreciated today.',
                'Read a story aloud and talk about how each character felt.',
                'Make handmade thank-you cards for three people who helped you.',
                'Take turns being the family "reporter" for the day.',
            ],
            'MIDDLE': [
                'Join a debate or public-speaking club and speak once a week.',
                'Interview a family member and write up their story.',
                'Mediate one disagreement a week and note what worked.',
                'Write and deliver a two-minute speech at a family event.',
            ],
            'SENIOR': [
                'Take a formal public-speaking course or competition.',
                'Run a peer mentoring session for younger students.',
                'Write an opinion piece for a school publication.',
                'Host a podcast episode interviewing someone in your community.',
            ],
        },
        'domains': [
            'Law & Advocacy',
            'Psychology & Counselling',
            'Teaching & Educational Leadership',
            'Public Relations & Community Management',
        ],
    },
    ('SPATIAL', 'ARTS'): {
        'title': 'The Visual Designer',
        'summary': (
            'Your child thinks in pictures — shape, layout, depth and how things fit together in '
            'space. Combined with a love of creative expression, that mental imagery lands on the '
            'page as strong visual design. They can picture the finished thing before they start, '
            'which is a rare and very useful skill.'
        ),
        'activities': {
            'JUNIOR': [
                'Build and redraw a block tower from three different viewpoints.',
                'Make a collage of overlapping shapes and talk about what is in front.',
                'Try a mystery-drawing game: describe a shape for someone to copy.',
                'Fold paper into 3D animals and decorate them.',
            ],
            'MIDDLE': [
                'Design a poster with a clear focal point and visual hierarchy.',
                'Practise one-point perspective with a streetscape sketch.',
                'Make a simple stop-motion animation from paper cut-outs.',
                'Redesign a board-game cover with your own layout.',
            ],
            'SENIOR': [
                'Learn a vector tool and design a logo with three variations.',
                'Build a 3D model of a room in free software.',
                'Produce a short stop-motion or motion-graphics clip.',
                'Take a photo series exploring light and shadow and mock it up as a zine.',
            ],
        },
        'domains': [
            'Graphic & Product Design',
            'Architecture & Interior Design',
            'Animation & Visual Effects',
            'UX/UI Design & Human Factors',
        ],
    },
    ('SPATIAL', 'STEM'): {
        'title': 'The Master Builder',
        'summary': (
            'Your child has an exceptional sense of space: how parts relate, rotate and assemble. '
            'That instinct meets a love of science and engineering perfectly, turning ideas into '
            'physical models and working machines. They learn best with their hands on the parts.'
        ),
        'activities': {
            'JUNIOR': [
                'Build a bridge from paper or straws that holds a book.',
                'Copy a tangram puzzle picture using all seven pieces.',
                'Make a cardboard marble run and improve one corner of it.',
                'Recreate a simple machine from a picture, then test it.',
            ],
            'MIDDLE': [
                'Design and build a catapult, then measure the range.',
                'Sketch a floor plan of your room to scale.',
                'Assemble a robotics or electronics starter kit.',
                'Build a weight-bearing tower from a single sheet of paper.',
            ],
            'SENIOR': [
                'Learn 3D CAD and print or model a functional part.',
                'Build a motorised device and iterate on the design twice.',
                'Model a structure and test it under load.',
                'Design an ergonomic object and refine it from user feedback.',
            ],
        },
        'domains': [
            'Civil & Structural Engineering',
            'Industrial & Product Design',
            'Robotics & Mechatronics',
            'Architecture & Urban Planning',
        ],
    },
    ('SPATIAL', 'NATURE'): {
        'title': 'The Explorer Naturalist',
        'summary': (
            'Your child maps the physical world in their head: directions, distances, terrain and '
            'where things are found. Add a real love of the outdoors and they become an explorer '
            'who can navigate, record and find their way to the interesting places. Learning '
            'outside is where they come alive.'
        ),
        'activities': {
            'JUNIOR': [
                'Draw a map of your garden or local park with landmarks.',
                'Go on a shape hunt outdoors for spirals, circles and symmetry.',
                'Build a den from natural materials and mark it on your map.',
                'Collect and arrange pebbles from smallest to largest.',
            ],
            'MIDDLE': [
                'Draw an accurate to-scale map of a local trail.',
                'Learn to use a compass and take a bearing.',
                'Track animal prints and mark sightings on a map.',
                'Build a simple shelter from natural materials and test it.',
            ],
            'SENIOR': [
                'Plan and lead a navigation hike with a route card.',
                'Create a GIS-style map of a local habitat in free software.',
                'Learn basic orienteering and enter a local course.',
                'Document trail conditions and submit real observations to a citizen-science project.',
            ],
        },
        'domains': [
            'Geology & Earth Sciences',
            'Cartography & Geospatial Analysis',
            'Outdoor Education & Expedition Leadership',
            'Marine Biology & Oceanography',
        ],
    },
    ('SPATIAL', 'SOCIAL'): {
        'title': 'The Team Architect',
        'summary': (
            'Your child sees how things and people fit together in space and in a group. They are '
            'good at arranging the room, the team and the plan so everything runs smoothly. That '
            'combination of spatial planning and social awareness makes them a calm organiser in '
            'group projects.'
        ),
        'activities': {
            'JUNIOR': [
                'Design and set up an obstacle course for friends to run.',
                'Arrange the room for a family game night and brief everyone.',
                'Build a shared fort where each person owns one section.',
                'Draw a seating plan for a party and explain your choices.',
            ],
            'MIDDLE': [
                'Plan the layout for a small school event and mark exits.',
                'Organise a team scavenger hunt with a map per group.',
                'Design a shared workspace for a group project.',
                'Run a build challenge where pairs must agree on the design.',
            ],
            'SENIOR': [
                'Manage the spatial logistics of a school event end to end.',
                'Design an accessible space and present the reasoning.',
                'Lead a team build (shelter, set, stall) against a deadline.',
                'Propose a redesign of a shared school space with mock-ups.',
            ],
        },
        'domains': [
            'Event & Production Management',
            'Urban Planning & Community Design',
            'Sports Coaching & Performance Analysis',
            'Project & Construction Management',
        ],
    },
    ('CRITICAL', 'STEM'): {
        'title': 'The Problem Solver',
        'summary': (
            'Your child questions things before accepting them and looks for the reason behind an '
            'answer. That critical instinct is exactly what science rewards, so they naturally '
            'test ideas instead of memorising them. Expect plenty of "but why?" — it is their '
            'best thinking tool.'
        ),
        'activities': {
            'JUNIOR': [
                'Run a fair test: change one thing and keep the rest the same.',
                'Predict what will happen, then check and say what surprised you.',
                'Sort toys into "works forever" and "needs a battery".',
                'Spot the silly mistake in a made-up science story.',
            ],
            'MIDDLE': [
                'Design a fair-test experiment and write up the conclusion.',
                'Compare two adverts and identify the claims that cannot be proven.',
                'Keep a "questions I could not answer yet" list and revisit it.',
                'Debug a simple block-program and explain the error.',
            ],
            'SENIOR': [
                'Evaluate two news sources on the same science story.',
                'Design and run an experiment with a control group.',
                'Learn to spot logical fallacies and collect real examples.',
                'Reproduce a public data claim and check whether it holds.',
            ],
        },
        'domains': [
            'Research Science & Experimental Design',
            'Data Science & Analytics',
            'Forensic Science & Investigation',
            'Engineering R&D',
        ],
    },
    ('CRITICAL', 'ARTS'): {
        'title': 'The Thoughtful Creator',
        'summary': (
            'Your child analyses before they build, asking what a piece is trying to say and '
            'whether it succeeds. That critical eye is a genuine creative advantage: it means '
            'their work is intentional rather than accidental. They will revise a piece until it '
            'matches the idea in their head.'
        ),
        'activities': {
            'JUNIOR': [
                'Look at a painting and say what you think is happening and why.',
                'Make a picture, then change one thing to make it better.',
                'Tell a story three ways and pick the best ending together.',
                'Spot the difference between two versions of the same drawing.',
            ],
            'MIDDLE': [
                'Write a review of a film or book with reasons for each opinion.',
                'Revise one piece of work three times and compare the drafts.',
                'Curate a small gallery of five images with a shared theme.',
                'Analyse why a song works: tempo, lyrics, structure.',
            ],
            'SENIOR': [
                'Write a critical essay on a piece of media you admire.',
                'Run a structured critique session on a peer\'s work.',
                'Compare two adaptations of the same story and argue which is stronger.',
                'Keep a design notebook documenting what you changed and why.',
            ],
        },
        'domains': [
            'Art Criticism & Curation',
            'Film & Media Studies',
            'Design Research & Strategy',
            'Copywriting & Creative Direction',
        ],
    },
    ('CRITICAL', 'NATURE'): {
        'title': 'The Eco Detective',
        'summary': (
            'Your child asks the hard questions about the world around them: what caused this, '
            'what happens next, and who is affected. Applied to nature, that instinct turns into '
            'sharp environmental thinking. They are drawn to causes rather than just facts.'
        ),
        'activities': {
            'JUNIOR': [
                'Follow one piece of litter and work out where it could end up.',
                'Ask "what would happen if the bees disappeared?" and draw the chain.',
                'Sort household waste into what can and cannot be recycled.',
                'Watch a puddle for a week and record what changes.',
            ],
            'MIDDLE': [
                'Audit your household waste for a week and suggest three fixes.',
                'Trace the journey of one item from raw material to bin.',
                'Compare two local green spaces and critique their design.',
                'Build a compost system and monitor it for four weeks.',
            ],
            'SENIOR': [
                'Research a local environmental issue and write a position paper.',
                'Model the carbon impact of one household habit change.',
                'Design a school recycling or energy plan and cost it out.',
                'Review an environmental policy and identify the gaps.',
            ],
        },
        'domains': [
            'Environmental Policy & Law',
            'Sustainability Consulting',
            'Climate Science & Modelling',
            'Wildlife Conservation Management',
        ],
    },
    ('CRITICAL', 'SOCIAL'): {
        'title': 'The Empathetic Leader',
        'summary': (
            'Your child thinks carefully about consequences and about people at the same time. '
            'They notice unfairness quickly and want to understand it before they act. That '
            'combination makes them the kind of leader a group trusts — fair, considered and '
            'willing to speak up.'
        ),
        'activities': {
            'JUNIOR': [
                'Talk through a story where someone was treated unfairly and decide what to do.',
                'Take on one helping job at home and do it without reminders.',
                'Play a co-operative board game where everyone must win together.',
                'Practise asking "how do you think that made them feel?"',
            ],
            'MIDDLE': [
                'Run a small service project from idea to completion.',
                'Debate both sides of a fairness question in class.',
                'Set up a peer buddy system for a younger class.',
                'Research a social issue and present three practical solutions.',
            ],
            'SENIOR': [
                'Lead a fundraising or awareness campaign with a measurable goal.',
                'Model the impact of a policy decision on different groups.',
                'Take a peer-support or mentoring role with training.',
                'Write a reasoned proposal for a change at your school and pitch it.',
            ],
        },
        'domains': [
            'Behavioral Psychology & Counselling',
            'Social Work & NGO Leadership',
            'Law & Human Rights',
            'Organisational Leadership & HR',
        ],
    },
}


def _norm_category_scores(session):
    """Return {code: 0-100 int} for every category the session answered."""
    earned = defaultdict(int)
    possible = defaultdict(int)

    responses = session.responses.select_related(
        'selected_choice', 'question', 'question__category'
    )
    for response in responses:
        code = response.question.category.code
        earned[code] += response.earned_points
        possible[code] += response.max_points

    scores = {}
    for code, max_points in possible.items():
        if max_points <= 0:
            scores[code] = 0
        else:
            scores[code] = round((earned[code] / max_points) * 100)
    return scores


def generate_assessment_result(session):
    """Score a session and persist its ``AssessmentResult`` (idempotent)."""
    scores = _norm_category_scores(session)

    aptitude_scores = {c: scores.get(c, 0) for c in APTITUDE_CODES}
    interest_scores = {c: scores.get(c, 0) for c in INTEREST_CODES}

    overall = round(
        sum(aptitude_scores.values()) / len(APTITUDE_CODES), 2
    )

    dominant_aptitude_code = max(APTITUDE_CODES, key=lambda c: aptitude_scores[c])
    dominant_interest_code = max(INTEREST_CODES, key=lambda c: interest_scores[c])

    persona = PERSONA_MATRIX[(dominant_aptitude_code, dominant_interest_code)]
    activities = persona['activities'].get(
        session.child.age_group, persona['activities']['MIDDLE']
    )

    result, _ = AssessmentResult.objects.update_or_create(
        session=session,
        defaults={
            'aptitude_scores': aptitude_scores,
            'interest_scores': interest_scores,
            'overall_aptitude_percentage': overall,
            'dominant_aptitude': Category.objects.filter(
                code=dominant_aptitude_code
            ).first(),
            'dominant_interest': Category.objects.filter(
                code=dominant_interest_code
            ).first(),
            'persona_title': persona['title'],
            'persona_summary': persona['summary'],
            'recommended_activities': list(activities),
            'recommended_future_domains': list(persona['domains']),
        },
    )
    return result
