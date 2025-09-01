# core/management/commands/seed_sources.py
from django.core.management.base import BaseCommand
from core.models import Source, SourceType, Category

SOURCES = [
    # -------- Existing (jobs)
    {"name": "RemoteOK", "url": "https://remoteok.com", "type": SourceType.WEBSITE, "category": Category.JOB, "parser": "scrape_remoteok"},
    {"name": "Remotive", "url": "https://remotive.com", "type": SourceType.WEBSITE, "category": Category.JOB, "parser": "scrape_remotive"},
    {"name": "We Work Remotely", "url": "https://weworkremotely.com", "type": SourceType.WEBSITE, "category": Category.JOB, "parser": "scrape_wwr"},
    {"name": "Remote.co", "url": "https://remote.co", "type": SourceType.WEBSITE, "category": Category.JOB, "parser": "scrape_remote_co"},
    {"name": "JustRemote", "url": "https://justremote.co", "type": SourceType.WEBSITE, "category": Category.JOB, "parser": "scrape_justremote"},
    {"name": "Wellfound (AngelList)", "url": "https://wellfound.com", "type": SourceType.WEBSITE, "category": Category.JOB, "parser": "scrape_wellfound"},

    # -------- New job boards (with scrapers already in code)
    {"name": "Working Nomads", "url": "https://www.workingnomads.com/jobs", "type": SourceType.WEBSITE, "category": Category.JOB, "parser": "scrape_working_nomads"},
    {"name": "NoDesk", "url": "https://nodesk.co/remote-jobs/", "type": SourceType.WEBSITE, "category": Category.JOB, "parser": "scrape_nodesk"},
    {"name": "Jobspresso", "url": "https://jobspresso.co/remote-work/", "type": SourceType.WEBSITE, "category": Category.JOB, "parser": "scrape_jobspresso"},
    {"name": "Arc.dev", "url": "https://arc.dev/remote-jobs", "type": SourceType.WEBSITE, "category": Category.JOB, "parser": "scrape_arc"},

    # -------- Extra global remote job boards (wired to scrapers)
    {"name": "Himalayas",      "url": "https://himalayas.app/jobs",           "type": SourceType.WEBSITE, "category": Category.JOB, "parser": "scrape_himalayas"},
    {"name": "remote.io",      "url": "https://remote.io/remote-jobs",        "type": SourceType.WEBSITE, "category": Category.JOB, "parser": "scrape_remote_io"},
    {"name": "SkipTheDrive",   "url": "https://skipthedrive.com/remote-jobs/","type": SourceType.WEBSITE, "category": Category.JOB, "parser": "scrape_skipthedrive"},
    {"name": "Jobicy",         "url": "https://jobicy.com/remote-jobs",       "type": SourceType.WEBSITE, "category": Category.JOB, "parser": "scrape_jobicy"},
    {"name": "Remotees",       "url": "https://remotees.com/remote-jobs",     "type": SourceType.WEBSITE, "category": Category.JOB, "parser": "scrape_remotees"},
    {"name": "Remotely.jobs",  "url": "https://remotely.jobs/",               "type": SourceType.WEBSITE, "category": Category.JOB, "parser": "scrape_remotely_jobs"},
    {"name": "Weremoto",       "url": "https://weremoto.com/remote-jobs",     "type": SourceType.WEBSITE, "category": Category.JOB, "parser": "scrape_weremoto"},
    {"name": "RemoteTechJobs", "url": "https://remotetechjobs.com/",          "type": SourceType.WEBSITE, "category": Category.JOB, "parser": "scrape_remote_tech_jobs"},
    {"name": "PowerToFly",     "url": "https://powertofly.com/jobs?location=Remote", "type": SourceType.WEBSITE, "category": Category.JOB, "parser": "scrape_powertofly"},
    {"name": "FreshRemote",    "url": "https://freshremote.work/",            "type": SourceType.WEBSITE, "category": Category.JOB, "parser": "scrape_freshremote"},
    {"name": "Authentic Jobs", "url": "https://www.authenticjobs.com/?location=remote", "type": SourceType.WEBSITE, "category": Category.JOB, "parser": "scrape_authentic_jobs"},
    {"name": "No Fluff Jobs",  "url": "https://nofluffjobs.com/remote",       "type": SourceType.WEBSITE, "category": Category.JOB, "parser": "scrape_nofluffjobs"},
    {"name": "The Hub",        "url": "https://thehub.io/jobs?location=remote","type": SourceType.WEBSITE, "category": Category.JOB, "parser": "scrape_the_hub"},

    # -------- Projects/competitions (wired to scrapers)
    {"name": "Devpost",     "url": "https://devpost.com",                             "type": SourceType.WEBSITE, "category": Category.PROJECT,     "parser": "scrape_devpost"},
    {"name": "HackerEarth Challenges", "url": "https://www.hackerearth.com/challenges/","type": SourceType.WEBSITE, "category": Category.PROJECT,  "parser": "scrape_hackerearth"},
    {"name": "Devfolio Hackathons",    "url": "https://devfolio.co/hackathons",         "type": SourceType.WEBSITE, "category": Category.PROJECT,  "parser": "scrape_devfolio"},
    {"name": "Kaggle",      "url": "https://www.kaggle.com/competitions",             "type": SourceType.WEBSITE, "category": Category.COMPETITION, "parser": "scrape_kaggle"},
    {"name": "Gitcoin",     "url": "https://gitcoin.co/grants/explorer",              "type": SourceType.WEBSITE, "category": Category.PROJECT,     "parser": "scrape_gitcoin"},
    {"name": "TAIKAI",      "url": "https://taikai.network/hackathons",               "type": SourceType.WEBSITE, "category": Category.PROJECT,     "parser": "scrape_taikai"},
    {"name": "MLH",         "url": "https://mlh.io/seasons",                          "type": SourceType.WEBSITE, "category": Category.PROJECT,     "parser": "scrape_mlh"},
    {"name": "itch.io Jams","url": "https://itch.io/jams",                            "type": SourceType.WEBSITE, "category": Category.PROJECT,     "parser": "scrape_itch_io_jams"},
    {"name": "CodaLab",     "url": "https://codalab.lisn.upsaclay.fr/competitions/",  "type": SourceType.WEBSITE, "category": Category.PROJECT,     "parser": "scrape_codalab"},
    {"name": "Product Hunt","url": "https://www.producthunt.com/posts",               "type": SourceType.WEBSITE, "category": Category.PROJECT,     "parser": "scrape_product_hunt"},

    # -------- Freelance / gig marketplaces (PROJECT)
    {"name": "Freelancer.com", "url": "https://www.freelancer.com/jobs/",      "type": SourceType.WEBSITE, "category": Category.PROJECT, "parser": "scrape_freelancer_com"},
    {"name": "PeoplePerHour",  "url": "https://www.peopleperhour.com/freelance-jobs", "type": SourceType.WEBSITE, "category": Category.PROJECT, "parser": "scrape_peopleperhour"},
    {"name": "Guru",           "url": "https://www.guru.com/work/",            "type": SourceType.WEBSITE, "category": Category.PROJECT, "parser": "scrape_guru"},
    {"name": "Contra",         "url": "https://contra.com/jobs",               "type": SourceType.WEBSITE, "category": Category.PROJECT, "parser": "scrape_contra"},
    {"name": "Braintrust",     "url": "https://www.usebraintrust.com/jobs",    "type": SourceType.WEBSITE, "category": Category.PROJECT, "parser": "scrape_braintrust"},
    {"name": "Gun.io",         "url": "https://gun.io/",                       "type": SourceType.WEBSITE, "category": Category.PROJECT, "parser": "scrape_gunio"},
    {"name": "Flexiple",       "url": "https://flexiple.com/freelance-jobs/",  "type": SourceType.WEBSITE, "category": Category.PROJECT, "parser": "scrape_flexiple"},
    {"name": "Topcoder",       "url": "https://www.topcoder.com/challenges",   "type": SourceType.WEBSITE, "category": Category.PROJECT, "parser": "scrape_topcoder"},
    {"name": "Dribbble Jobs",  "url": "https://dribbble.com/jobs?location=remote", "type": SourceType.WEBSITE, "category": Category.PROJECT, "parser": "scrape_dribbble_jobs"},
    {"name": "Behance Jobs",   "url": "https://www.behance.net/joblist?location=remote", "type": SourceType.WEBSITE, "category": Category.PROJECT, "parser": "scrape_behance_jobs"},
    {"name": "Twine",          "url": "https://www.twine.net/jobs",           "type": SourceType.WEBSITE, "category": Category.PROJECT, "parser": "scrape_twine"},
    {"name": "Workana",        "url": "https://www.workana.com/en/jobs",      "type": SourceType.WEBSITE, "category": Category.PROJECT, "parser": "scrape_workana"},
    {"name": "Freelancermap",  "url": "https://www.freelancermap.com/it-projects", "type": SourceType.WEBSITE, "category": Category.PROJECT, "parser": "scrape_freelancermap"},
    {"name": "Truelancer",     "url": "https://www.truelancer.com/freelance-jobs", "type": SourceType.WEBSITE, "category": Category.PROJECT, "parser": "scrape_truelancer"},
    # Sites we can’t reliably scrape without JS/login (safe stubs exist to return []):
    {"name": "Upwork",         "url": "https://www.upwork.com/",              "type": SourceType.WEBSITE, "category": Category.PROJECT, "parser": "scrape_upwork"},
    {"name": "Fiverr",         "url": "https://www.fiverr.com/",              "type": SourceType.WEBSITE, "category": Category.PROJECT, "parser": "scrape_fiverr"},
    {"name": "Toptal",         "url": "https://www.toptal.com/",              "type": SourceType.WEBSITE, "category": Category.PROJECT, "parser": "scrape_toptal"},
    {"name": "Lemons",         "url": "https://www.lemons.io/",               "type": SourceType.WEBSITE, "category": Category.PROJECT, "parser": "scrape_lemons"},
    {"name": "Malt",           "url": "https://www.malt.com/",                "type": SourceType.WEBSITE, "category": Category.PROJECT, "parser": "scrape_malt"},
    {"name": "99designs",      "url": "https://99designs.com/",               "type": SourceType.WEBSITE, "category": Category.PROJECT, "parser": "scrape_99designs"},

    # -------- Iranian job boards (JOB) — ACTIVE (no remote filter)
    {"name": "Jobinja",      "url": "https://jobinja.ir/jobs",               "type": SourceType.WEBSITE, "category": Category.JOB, "parser": "scrape_jobinja"},
    {"name": "JobVision",    "url": "https://jobvision.ir/jobs",             "type": SourceType.WEBSITE, "category": Category.JOB, "parser": "scrape_jobvision"},
    {"name": "IranTalent",   "url": "https://www.irantalent.com/jobs",       "type": SourceType.WEBSITE, "category": Category.JOB, "parser": "scrape_irantalent"},
    {"name": "Karboom",      "url": "https://karboom.io/jobs",               "type": SourceType.WEBSITE, "category": Category.JOB, "parser": "scrape_karboom"},
    {"name": "e-Estekhdam",  "url": "https://www.e-estekhdam.com/",          "type": SourceType.WEBSITE, "category": Category.JOB, "parser": "scrape_e_estekhdam"},
    {"name": "Quera Jobs",   "url": "https://quera.org/jobs",                "type": SourceType.WEBSITE, "category": Category.JOB, "parser": "scrape_quera_jobs"},

    # -------- Iranian freelance / project boards (PROJECT) — ACTIVE
    {"name": "Ponisha",      "url": "https://ponisha.ir/search/projects",    "type": SourceType.WEBSITE, "category": Category.PROJECT, "parser": "scrape_ponisha"},
    {"name": "ParsCoders",   "url": "https://parscoders.com/project/list/",  "type": SourceType.WEBSITE, "category": Category.PROJECT, "parser": "scrape_parscoders"},

    # -------- Telegram channels (existing)
    {"name": "@remotejobs",          "url": "https://t.me/remotejobs",            "type": SourceType.TELEGRAM_CHANNEL, "category": Category.JOB, "parser": ""},
    {"name": "@weworkremotely",      "url": "https://t.me/weworkremotely",        "type": SourceType.TELEGRAM_CHANNEL, "category": Category.JOB, "parser": ""},
    {"name": "@remoteworkers",       "url": "https://t.me/remoteworkers",         "type": SourceType.TELEGRAM_CHANNEL, "category": Category.JOB, "parser": ""},

    # -------- Telegram channels (you provided earlier)
    {"name": "@freelancer_job",      "url": "https://t.me/freelancer_job",        "type": SourceType.TELEGRAM_CHANNEL, "category": Category.JOB, "parser": ""},
    {"name": "@FreelancerH",         "url": "https://t.me/FreelancerH",           "type": SourceType.TELEGRAM_CHANNEL, "category": Category.JOB, "parser": ""},
    {"name": "@Daneshjoo_Com",       "url": "https://t.me/Daneshjoo_Com",         "type": SourceType.TELEGRAM_CHANNEL, "category": Category.JOB, "parser": ""},
    {"name": "@DorkariLand",         "url": "https://t.me/DorkariLand",           "type": SourceType.TELEGRAM_CHANNEL, "category": Category.JOB, "parser": ""},
    {"name": "@Collegian_Projection","url": "https://t.me/Collegian_Projection",  "type": SourceType.TELEGRAM_CHANNEL, "category": Category.JOB, "parser": ""},
    {"name": "@doorkaari",           "url": "https://t.me/doorkaari",             "type": SourceType.TELEGRAM_CHANNEL, "category": Category.JOB, "parser": ""},

    # -------- More global Telegram channels
    {"name": "@remotejobshq",        "url": "https://t.me/remotejobshq",          "type": SourceType.TELEGRAM_CHANNEL, "category": Category.JOB, "parser": ""},
    {"name": "@remote_devs_jobs",    "url": "https://t.me/remote_devs_jobs",      "type": SourceType.TELEGRAM_CHANNEL, "category": Category.JOB, "parser": ""},
    {"name": "@python_jobs_feed",    "url": "https://t.me/python_jobs_feed",      "type": SourceType.TELEGRAM_CHANNEL, "category": Category.JOB, "parser": ""},
    {"name": "@golangjob",           "url": "https://t.me/golangjob",             "type": SourceType.TELEGRAM_CHANNEL, "category": Category.JOB, "parser": ""},
    {"name": "@js_jobs_feed",        "url": "https://t.me/js_jobs_feed",          "type": SourceType.TELEGRAM_CHANNEL, "category": Category.JOB, "parser": ""},
    {"name": "@ai_ml_jobs",          "url": "https://t.me/ai_ml_jobs",            "type": SourceType.TELEGRAM_CHANNEL, "category": Category.JOB, "parser": ""},

    # -------- Your new Telegram channels (added if not already present)
    {"name": "@Freelancer_Booth",    "url": "https://t.me/Freelancer_Booth",      "type": SourceType.TELEGRAM_CHANNEL, "category": Category.JOB, "parser": ""},
    {"name": "@WeProje",             "url": "https://t.me/WeProje",               "type": SourceType.TELEGRAM_CHANNEL, "category": Category.JOB, "parser": ""},
    {"name": "@SevenProzhe",         "url": "https://t.me/SevenProzhe",           "type": SourceType.TELEGRAM_CHANNEL, "category": Category.JOB, "parser": ""},
    {"name": "@ZFreelancer",         "url": "https://t.me/ZFreelancer",           "type": SourceType.TELEGRAM_CHANNEL, "category": Category.JOB, "parser": ""},
    {"name": "@AloFreelancer",       "url": "https://t.me/AloFreelancer",         "type": SourceType.TELEGRAM_CHANNEL, "category": Category.JOB, "parser": ""},
    {"name": "@cproje",              "url": "https://t.me/cproje",                "type": SourceType.TELEGRAM_CHANNEL, "category": Category.JOB, "parser": ""},
    {"name": "@uprojeh",             "url": "https://t.me/uprojeh",               "type": SourceType.TELEGRAM_CHANNEL, "category": Category.JOB, "parser": ""},
    {"name": "@freelaancing",        "url": "https://t.me/freelaancing",          "type": SourceType.TELEGRAM_CHANNEL, "category": Category.JOB, "parser": ""},
]



class Command(BaseCommand):
    help = "Seed default sources"

    def handle(self, *args, **options):
        created = 0
        for s in SOURCES:
            obj, was_created = Source.objects.update_or_create(
                name=s["name"],
                defaults={
                    "url": s["url"],
                    "type": s["type"],
                    "category": s["category"],
                    "parser": s.get("parser", ""),
                    "is_active": True,
                },
            )
            if was_created:
                created += 1
        self.stdout.write(self.style.SUCCESS(f"Seeded/ensured {len(SOURCES)} sources (new: {created})."))



