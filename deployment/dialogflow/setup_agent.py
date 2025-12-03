#!/usr/bin/env python3
"""
PawConnect Dialogflow CX Agent Setup
====================================

This script is the ONLY script you need to set up or update your Dialogflow CX agent.

It handles:
- Auto-detection of agent ID (or manual specification)
- Entity types (pet_species, pet_size, pet_age_group, housing_type)
- Intents with parameter annotations (search_pets, get_recommendations, etc.)
- Pages and flows with proper transition routes
- Webhook configuration
- Welcome message

Can be run multiple times safely - it updates existing resources.

Usage:
    # Auto-detect agent (recommended)
    python deployment/dialogflow/setup_agent.py --project-id YOUR_PROJECT_ID

    # Specify agent ID manually
    python deployment/dialogflow/setup_agent.py \\
        --project-id YOUR_PROJECT_ID \\
        --agent-id YOUR_AGENT_ID

    # Include webhook URL
    python deployment/dialogflow/setup_agent.py \\
        --project-id YOUR_PROJECT_ID \\
        --webhook-url https://your-webhook-url/webhook
"""

import sys
import os
from pathlib import Path
from typing import Optional, List, Dict
from google.cloud.dialogflowcx_v3 import (
    AgentsClient,
    IntentsClient,
    EntityTypesClient,
    PagesClient,
    FlowsClient,
    WebhooksClient
)
from google.cloud.dialogflowcx_v3.types import (
    Intent,
    EntityType,
    Page,
    Flow,
    Form,
    Fulfillment,
    ResponseMessage,
    TransitionRoute,
    EventHandler,
    Webhook
)
from google.api_core.client_options import ClientOptions
from google.protobuf import field_mask_pb2
from loguru import logger

# Try to load .env file
try:
    from dotenv import load_dotenv
    # Look for .env in project root (2 levels up from this script)
    env_path = Path(__file__).parent.parent.parent / ".env"
    if env_path.exists():
        load_dotenv(env_path)
        logger.info(f"Loaded environment variables from {env_path}")
except ImportError:
    # python-dotenv not installed, skip loading .env
    pass


class DialogflowSetup:
    """Complete Dialogflow CX agent setup."""

    def __init__(
        self,
        project_id: str,
        agent_id: str,
        location: str = "us-central1",
        webhook_url: Optional[str] = None
    ):
        self.project_id = project_id
        self.agent_id = agent_id
        self.location = location
        self.webhook_url = webhook_url

        # Build paths
        self.agent_path = f"projects/{project_id}/locations/{location}/agents/{agent_id}"
        self.api_endpoint = f"{location}-dialogflow.googleapis.com"
        self.client_options = ClientOptions(api_endpoint=self.api_endpoint)

        # Initialize clients
        self.agents_client = AgentsClient(client_options=self.client_options)
        self.intents_client = IntentsClient(client_options=self.client_options)
        self.entity_types_client = EntityTypesClient(client_options=self.client_options)
        self.pages_client = PagesClient(client_options=self.client_options)
        self.flows_client = FlowsClient(client_options=self.client_options)
        self.webhooks_client = WebhooksClient(client_options=self.client_options)

        # Cache for lookups
        self._entity_types_cache = {}
        self._intents_cache = {}

    def get_or_create_entity_type(self, display_name: str, entities: List[Dict]) -> EntityType:
        """Get existing entity type or create new one."""
        if display_name in self._entity_types_cache:
            return self._entity_types_cache[display_name]

        # Try to find existing
        entity_types_list = list(self.entity_types_client.list_entity_types(parent=self.agent_path))
        for entity_type in entity_types_list:
            if entity_type.display_name == display_name:
                logger.info(f"  Found existing entity type: {display_name}")

                # Update it with new entities
                entity_type.entities.clear()
                entity_type.entities.extend([
                    EntityType.Entity(value=e["value"], synonyms=e["synonyms"])
                    for e in entities
                ])
                entity_type.enable_fuzzy_extraction = True

                updated = self.entity_types_client.update_entity_type(entity_type=entity_type)
                logger.info(f"  ✓ Updated entity type with {len(entities)} entities")
                self._entity_types_cache[display_name] = updated
                return updated

        # Create new
        logger.info(f"  Creating new entity type: {display_name}")
        entity_type = EntityType(
            display_name=display_name,
            kind=EntityType.Kind.KIND_MAP,
            entities=[
                EntityType.Entity(value=e["value"], synonyms=e["synonyms"])
                for e in entities
            ],
            enable_fuzzy_extraction=True
        )

        created = self.entity_types_client.create_entity_type(
            parent=self.agent_path,
            entity_type=entity_type
        )
        logger.info(f"  ✓ Created entity type with {len(entities)} entities")
        self._entity_types_cache[display_name] = created
        return created

    def get_or_create_intent(
        self,
        display_name: str,
        training_phrases: List[List[Dict]],
        parameters: Optional[List[Dict]] = None
    ) -> Intent:
        """Get existing intent or create new one."""
        if display_name in self._intents_cache:
            return self._intents_cache[display_name]

        # Try to find existing
        intents_list = list(self.intents_client.list_intents(parent=self.agent_path))
        for intent in intents_list:
            if intent.display_name == display_name:
                logger.info(f"  Found existing intent: {display_name}")

                # Update training phrases
                intent.training_phrases.clear()
                intent.training_phrases.extend([
                    Intent.TrainingPhrase(
                        parts=[
                            Intent.TrainingPhrase.Part(
                                text=part["text"],
                                parameter_id=part.get("parameter_id")
                            )
                            for part in phrase
                        ],
                        repeat_count=1
                    )
                    for phrase in training_phrases
                ])

                # Update parameters if provided
                if parameters:
                    intent.parameters.clear()
                    intent.parameters.extend([
                        Intent.Parameter(
                            id=param["id"],
                            entity_type=param["entity_type"]
                        )
                        for param in parameters
                    ])

                updated = self.intents_client.update_intent(intent=intent)
                logger.info(f"  ✓ Updated intent with {len(training_phrases)} training phrases")
                self._intents_cache[display_name] = updated
                return updated

        # Create new
        logger.info(f"  Creating new intent: {display_name}")
        intent = Intent(
            display_name=display_name,
            training_phrases=[
                Intent.TrainingPhrase(
                    parts=[
                        Intent.TrainingPhrase.Part(
                            text=part["text"],
                            parameter_id=part.get("parameter_id")
                        )
                        for part in phrase
                    ],
                    repeat_count=1
                )
                for phrase in training_phrases
            ],
            parameters=[
                Intent.Parameter(
                    id=param["id"],
                    entity_type=param["entity_type"]
                )
                for param in parameters
            ] if parameters else [],
            priority=500000
        )

        created = self.intents_client.create_intent(
            parent=self.agent_path,
            intent=intent
        )
        logger.info(f"  ✓ Created intent with {len(training_phrases)} training phrases")
        self._intents_cache[display_name] = created
        return created

    def setup_entity_types(self):
        """Create/update all entity types."""
        logger.info("Setting up entity types...")

        # Housing type
        self.get_or_create_entity_type(
            "housing_type",
            [
                {"value": "apartment", "synonyms": ["apartment", "apt", "flat", "apartments", "apartment building"]},
                {"value": "house", "synonyms": ["house", "home", "single family", "single-family home"]},
                {"value": "condo", "synonyms": ["condo", "condominium", "townhouse", "townhome"]},
                {"value": "own", "synonyms": ["own", "owner", "homeowner", "I own", "own my home"]},
                {"value": "rent", "synonyms": ["rent", "renter", "renting", "lease", "I rent", "renting a place"]},
                {"value": "live_with_family", "synonyms": ["live with family", "parents", "family home", "with parents", "parents house"]}
            ]
        )

        # Pet species
        self.get_or_create_entity_type(
            "pet_species",
            [
                {"value": "dog", "synonyms": ["dog", "dogs", "puppy", "puppies", "canine"]},
                {"value": "cat", "synonyms": ["cat", "cats", "kitten", "kittens", "feline"]},
                {"value": "rabbit", "synonyms": ["rabbit", "rabbits", "bunny", "bunnies"]},
                {"value": "bird", "synonyms": ["bird", "birds", "parrot", "parakeet"]},
                {"value": "small_animal", "synonyms": ["hamster", "guinea pig", "ferret"]}
            ]
        )

        # Dog breeds - comprehensive list
        self.get_or_create_entity_type(
            "dog_breed",
            [
                # Popular breeds
                {"value": "labrador retriever", "synonyms": ["labrador retriever", "labrador", "lab", "labs"]},
                {"value": "golden retriever", "synonyms": ["golden retriever", "golden", "goldens"]},
                {"value": "german shepherd", "synonyms": ["german shepherd", "gsd", "shepherd"]},
                {"value": "french bulldog", "synonyms": ["french bulldog", "frenchie", "french bull"]},
                {"value": "bulldog", "synonyms": ["bulldog", "english bulldog", "bull dog"]},
                {"value": "beagle", "synonyms": ["beagle", "beagles"]},
                {"value": "poodle", "synonyms": ["poodle", "standard poodle", "miniature poodle", "toy poodle"]},
                {"value": "rottweiler", "synonyms": ["rottweiler", "rottie", "rotty"]},
                {"value": "yorkshire terrier", "synonyms": ["yorkshire terrier", "yorkie", "yorkies"]},
                {"value": "boxer", "synonyms": ["boxer", "boxers"]},
                {"value": "dachshund", "synonyms": ["dachshund", "wiener dog", "doxie"]},

                # Working breeds
                {"value": "siberian husky", "synonyms": ["siberian husky", "husky", "huskies"]},
                {"value": "great dane", "synonyms": ["great dane", "dane"]},
                {"value": "doberman pinscher", "synonyms": ["doberman pinscher", "doberman", "dobie"]},
                {"value": "bernese mountain dog", "synonyms": ["bernese mountain dog", "bernese", "berner"]},
                {"value": "saint bernard", "synonyms": ["saint bernard", "st bernard"]},
                {"value": "mastiff", "synonyms": ["mastiff", "english mastiff"]},
                {"value": "rottweiler", "synonyms": ["rottweiler", "rottie"]},

                # Herding breeds
                {"value": "border collie", "synonyms": ["border collie", "collie"]},
                {"value": "australian shepherd", "synonyms": ["australian shepherd", "aussie", "aussies"]},
                {"value": "shetland sheepdog", "synonyms": ["shetland sheepdog", "sheltie"]},
                {"value": "corgi", "synonyms": ["corgi", "welsh corgi", "pembroke corgi", "cardigan corgi"]},

                # Toy/Small breeds
                {"value": "chihuahua", "synonyms": ["chihuahua", "chi"]},
                {"value": "pomeranian", "synonyms": ["pomeranian", "pom", "poms"]},
                {"value": "shih tzu", "synonyms": ["shih tzu", "shih-tzu"]},
                {"value": "maltese", "synonyms": ["maltese"]},
                {"value": "pug", "synonyms": ["pug", "pugs"]},
                {"value": "boston terrier", "synonyms": ["boston terrier", "boston"]},
                {"value": "cavalier king charles spaniel", "synonyms": ["cavalier king charles spaniel", "cavalier", "cavalier spaniel"]},

                # Sporting breeds
                {"value": "cocker spaniel", "synonyms": ["cocker spaniel", "cocker"]},
                {"value": "springer spaniel", "synonyms": ["springer spaniel", "english springer spaniel", "springer"]},
                {"value": "brittany", "synonyms": ["brittany", "brittany spaniel"]},
                {"value": "pointer", "synonyms": ["pointer", "german shorthaired pointer"]},
                {"value": "vizsla", "synonyms": ["vizsla"]},
                {"value": "weimaraner", "synonyms": ["weimaraner"]},

                # Terriers
                {"value": "jack russell terrier", "synonyms": ["jack russell terrier", "jack russell", "jrt"]},
                {"value": "bull terrier", "synonyms": ["bull terrier", "bully"]},
                {"value": "scottish terrier", "synonyms": ["scottish terrier", "scottie"]},
                {"value": "west highland terrier", "synonyms": ["west highland terrier", "westie"]},
                {"value": "airedale terrier", "synonyms": ["airedale terrier", "airedale"]},

                # Other popular breeds
                {"value": "pit bull", "synonyms": ["pit bull", "pitbull", "american pit bull terrier", "staffordshire terrier"]},
                {"value": "mixed breed", "synonyms": ["mixed breed", "mixed", "mutt", "mix"]},
                {"value": "unknown", "synonyms": ["unknown", "not sure", "don't know"]}
            ]
        )

        # Cat breeds - comprehensive list
        self.get_or_create_entity_type(
            "cat_breed",
            [
                # Popular breeds
                {"value": "domestic shorthair", "synonyms": ["domestic shorthair", "dsh", "short hair", "shorthair"]},
                {"value": "domestic longhair", "synonyms": ["domestic longhair", "dlh", "long hair", "longhair"]},
                {"value": "domestic medium hair", "synonyms": ["domestic medium hair", "dmh", "medium hair"]},
                {"value": "persian", "synonyms": ["persian", "persians"]},
                {"value": "maine coon", "synonyms": ["maine coon", "maine"]},
                {"value": "siamese", "synonyms": ["siamese", "siamese cat"]},
                {"value": "ragdoll", "synonyms": ["ragdoll", "rag doll"]},
                {"value": "bengal", "synonyms": ["bengal", "bengals"]},
                {"value": "british shorthair", "synonyms": ["british shorthair", "british short hair"]},
                {"value": "abyssinian", "synonyms": ["abyssinian", "aby"]},
                {"value": "birman", "synonyms": ["birman", "sacred cat of burma"]},
                {"value": "sphynx", "synonyms": ["sphynx", "sphinx", "hairless cat"]},
                {"value": "russian blue", "synonyms": ["russian blue", "russian"]},
                {"value": "scottish fold", "synonyms": ["scottish fold", "fold"]},
                {"value": "american shorthair", "synonyms": ["american shorthair", "american short hair"]},
                {"value": "devon rex", "synonyms": ["devon rex", "devon"]},
                {"value": "norwegian forest cat", "synonyms": ["norwegian forest cat", "norwegian forest", "wegie"]},
                {"value": "himalayan", "synonyms": ["himalayan", "himmy"]},
                {"value": "burmese", "synonyms": ["burmese"]},
                {"value": "oriental", "synonyms": ["oriental", "oriental shorthair"]},
                {"value": "manx", "synonyms": ["manx", "manx cat"]},
                {"value": "cornish rex", "synonyms": ["cornish rex", "cornish"]},
                {"value": "exotic shorthair", "synonyms": ["exotic shorthair", "exotic"]},
                {"value": "tonkinese", "synonyms": ["tonkinese", "tonk"]},
                {"value": "turkish angora", "synonyms": ["turkish angora", "angora"]},
                {"value": "tabby", "synonyms": ["tabby", "tabby cat"]},
                {"value": "tuxedo", "synonyms": ["tuxedo", "tuxedo cat"]},
                {"value": "calico", "synonyms": ["calico", "calico cat"]},
                {"value": "tortoiseshell", "synonyms": ["tortoiseshell", "tortie"]},
                {"value": "mixed breed", "synonyms": ["mixed breed", "mixed", "mix"]},
                {"value": "unknown", "synonyms": ["unknown", "not sure", "don't know"]}
            ]
        )

        # Pet size
        self.get_or_create_entity_type(
            "pet_size",
            [
                {"value": "small", "synonyms": ["small", "tiny", "little", "miniature"]},
                {"value": "medium", "synonyms": ["medium", "average", "mid-sized"]},
                {"value": "large", "synonyms": ["large", "big", "giant", "huge"]},
                {"value": "extra_large", "synonyms": ["extra-large", "xl", "giant", "huge", "very large"]}
            ]
        )

        # Pet age group
        self.get_or_create_entity_type(
            "pet_age_group",
            [
                {"value": "baby", "synonyms": ["baby", "newborn", "infant"]},
                {"value": "young", "synonyms": ["young", "puppy", "kitten", "juvenile"]},
                {"value": "adult", "synonyms": ["adult", "mature", "grown"]},
                {"value": "senior", "synonyms": ["senior", "elderly", "old", "older"]}
            ]
        )

        # Pet owner experience level
        self.get_or_create_entity_type(
            "experience_level",
            [
                {"value": "no_experience", "synonyms": ["no", "no experience", "never", "first time", "first-time owner", "new to pets", "I'm new", "never had a pet", "never owned", "beginner", "I don't have experience"]},
                {"value": "some_experience", "synonyms": ["some", "some experience", "a little", "limited", "had pets before", "grew up with pets", "childhood pet", "little bit"]},
                {"value": "experienced", "synonyms": ["yes", "experienced", "lots of experience", "very experienced", "expert", "had many pets", "owned pets before", "have experience", "I have experience", "plenty"]},
                {"value": "specific_breed", "synonyms": ["specific breed", "this breed", "same breed", "familiar with breed", "owned this breed", "had this breed before"]}
            ]
        )

        # Custom location entity (replaces @sys.location for better extraction)
        # Include major US cities and common ZIP code patterns
        self.get_or_create_entity_type(
            "location",
            [
                {"value": "Seattle", "synonyms": ["Seattle", "seattle", "98101", "98102", "98103", "98104", "98105", "98106", "98107", "98108", "98109", "98110", "98111", "98112", "98115", "98116", "98117", "98118", "98119", "98121", "98122", "98124", "98125", "98126", "98127", "98129", "98131", "98133", "98134", "98136", "98138", "98139", "98141", "98144", "98145", "98146", "98148", "98154", "98155", "98158", "98160", "98161", "98164", "98165", "98166", "98168", "98170", "98174", "98175", "98177", "98178", "98181", "98184", "98185", "98188", "98190", "98191", "98194", "98195", "98198", "98199"]},
                {"value": "Portland", "synonyms": ["Portland", "portland", "97201", "97202", "97203", "97204", "97205", "97206", "97209", "97210", "97211", "97212", "97213", "97214", "97215", "97216", "97217", "97218", "97219", "97220", "97221", "97222", "97223", "97224", "97225", "97227", "97228", "97229", "97230", "97231", "97232", "97233", "97236", "97239", "97240", "97242", "97251", "97253", "97254", "97256", "97266", "97267", "97268", "97269", "97280", "97281", "97282", "97283", "97286", "97290", "97291", "97292", "97293", "97294", "97296", "97298"]},
                {"value": "Boston", "synonyms": ["Boston", "boston", "02108", "02109", "02110", "02111", "02112", "02113", "02114", "02115", "02116", "02117", "02118", "02119", "02120", "02121", "02122", "02123", "02124", "02125", "02126", "02127", "02128", "02129", "02130", "02131", "02132", "02133", "02134", "02135", "02136", "02163", "02196", "02199", "02201", "02203", "02204", "02205", "02206", "02210", "02211", "02212", "02215", "02217", "02222", "02241", "02266", "02283", "02284", "02293", "02297", "02298"]},
                {"value": "San Francisco", "synonyms": ["San Francisco", "san francisco", "SF", "94102", "94103", "94104", "94105", "94107", "94108", "94109", "94110", "94111", "94112", "94114", "94115", "94116", "94117", "94118", "94119", "94120", "94121", "94122", "94123", "94124", "94125", "94126", "94127", "94128", "94129", "94130", "94131", "94132", "94133", "94134", "94137", "94139", "94140", "94141", "94142", "94143", "94144", "94145", "94146", "94147", "94151", "94158", "94159", "94160", "94161", "94163", "94164", "94172", "94177", "94188"]},
                {"value": "Los Angeles", "synonyms": ["Los Angeles", "los angeles", "LA", "90001", "90002", "90003", "90004", "90005", "90006", "90007", "90008", "90009", "90010", "90011", "90012", "90013", "90014", "90015", "90016", "90017", "90018", "90019", "90020", "90021", "90022", "90023", "90024", "90025", "90026", "90027", "90028", "90029", "90030", "90031", "90032", "90033", "90034", "90035", "90036", "90037", "90038", "90039", "90040", "90041", "90042", "90043", "90044", "90045", "90046", "90047", "90048", "90049", "90050", "90051", "90052", "90053", "90054", "90055", "90056", "90057", "90058", "90059", "90060", "90061", "90062", "90063", "90064", "90065", "90066", "90067", "90068", "90069", "90070", "90071", "90072", "90073", "90074", "90075", "90076", "90077", "90078", "90079", "90080", "90081", "90082", "90083", "90084", "90086", "90087", "90088", "90089", "90091", "90093", "90095", "90096", "90099"]},
                {"value": "New York", "synonyms": ["New York", "new york", "NYC", "New York City", "10001", "10002", "10003", "10004", "10005", "10006", "10007", "10009", "10010", "10011", "10012", "10013", "10014", "10016", "10017", "10018", "10019", "10020", "10021", "10022", "10023", "10024", "10025", "10026", "10027", "10028", "10029", "10030", "10031", "10032", "10033", "10034", "10035", "10036", "10037", "10038", "10039", "10040", "10041", "10043", "10044", "10045", "10055", "10060", "10065", "10069", "10075", "10080", "10081", "10087", "10090", "10095", "10103", "10104", "10105", "10106", "10107", "10108", "10109", "10110", "10111", "10112", "10115", "10118", "10119", "10120", "10121", "10122", "10123", "10128", "10151", "10152", "10153", "10154", "10155", "10158", "10162", "10165", "10166", "10167", "10168", "10169", "10170", "10171", "10172", "10173", "10174", "10175", "10176", "10177", "10178", "10179", "10185", "10199"]},
                {"value": "Chicago", "synonyms": ["Chicago", "chicago", "60601", "60602", "60603", "60604", "60605", "60606", "60607", "60608", "60609", "60610", "60611", "60612", "60613", "60614", "60615", "60616", "60617", "60618", "60619", "60620", "60621", "60622", "60623", "60624", "60625", "60626", "60628", "60629", "60630", "60631", "60632", "60633", "60634", "60636", "60637", "60638", "60639", "60640", "60641", "60642", "60643", "60644", "60645", "60646", "60647", "60649", "60651", "60652", "60653", "60654", "60655", "60656", "60657", "60659", "60660", "60661", "60666", "60668", "60669", "60670", "60673", "60674", "60675", "60677", "60678", "60680", "60681", "60682", "60684", "60685", "60686", "60687", "60688", "60689", "60690", "60691", "60693", "60694", "60695", "60696", "60697", "60699"]},
                {"value": "Denver", "synonyms": ["Denver", "denver", "80201", "80202", "80203", "80204", "80205", "80206", "80207", "80208", "80209", "80210", "80211", "80212", "80214", "80215", "80216", "80217", "80218", "80219", "80220", "80221", "80222", "80223", "80224", "80225", "80226", "80227", "80228", "80229", "80230", "80231", "80232", "80233", "80234", "80235", "80236", "80237", "80238", "80239", "80243", "80244", "80246", "80247", "80248", "80249", "80250", "80251", "80252", "80256", "80257", "80259", "80260", "80261", "80262", "80263", "80264", "80265", "80266", "80271", "80273", "80274", "80279", "80280", "80281", "80290", "80291", "80293", "80294", "80295", "80299"]},
                {"value": "Austin", "synonyms": ["Austin", "austin", "78701", "78702", "78703", "78704", "78705", "78712", "78717", "78719", "78721", "78722", "78723", "78724", "78725", "78726", "78727", "78728", "78729", "78730", "78731", "78732", "78733", "78734", "78735", "78736", "78737", "78738", "78739", "78741", "78742", "78744", "78745", "78746", "78747", "78748", "78749", "78750", "78751", "78752", "78753", "78754", "78755", "78756", "78757", "78758", "78759", "78760", "78761", "78762", "78763", "78764", "78765", "78766", "78767", "78768", "78769", "78772", "78773", "78774", "78778", "78779", "78783", "78799"]},
                {"value": "Phoenix", "synonyms": ["Phoenix", "phoenix", "85001", "85002", "85003", "85004", "85005", "85006", "85007", "85008", "85009", "85010", "85011", "85012", "85013", "85014", "85015", "85016", "85017", "85018", "85019", "85020", "85021", "85022", "85023", "85024", "85026", "85027", "85028", "85029", "85030", "85031", "85032", "85033", "85034", "85035", "85036", "85037", "85038", "85039", "85040", "85041", "85042", "85043", "85044", "85045", "85046", "85048", "85050", "85051", "85053", "85054", "85060", "85061", "85062", "85063", "85064", "85065", "85066", "85067", "85068", "85069", "85070", "85071", "85072", "85073", "85074", "85075", "85076", "85078", "85079", "85080"]}
            ]
        )

        logger.info("✓ Entity types configured")

    def setup_intents(self):
        """Create/update all intents."""
        logger.info("Setting up intents...")

        # Get system entity type paths
        sys_any = "projects/-/locations/-/agents/-/entityTypes/sys.any"
        sys_location = "projects/-/locations/-/agents/-/entityTypes/sys.location"

        # Get custom entity types from cache
        pet_species_entity = self._entity_types_cache.get("pet_species")
        pet_species_path = pet_species_entity.name if pet_species_entity else sys_any

        dog_breed_entity = self._entity_types_cache.get("dog_breed")
        dog_breed_path = dog_breed_entity.name if dog_breed_entity else sys_any

        cat_breed_entity = self._entity_types_cache.get("cat_breed")
        cat_breed_path = cat_breed_entity.name if cat_breed_entity else sys_any

        experience_level_entity = self._entity_types_cache.get("experience_level")
        experience_level_path = experience_level_entity.name if experience_level_entity else sys_any

        location_entity = self._entity_types_cache.get("location")
        location_path = location_entity.name if location_entity else sys_location

        # intent.search_pets with parameter annotations
        # Include complex, natural sentences that users actually say
        self.get_or_create_intent(
            "intent.search_pets",
            [
                # Simple patterns
                [{"text": "I want to adopt a "}, {"text": "dog", "parameter_id": "species"}, {"text": " in "}, {"text": "Seattle", "parameter_id": "location"}],
                [{"text": "Show me "}, {"text": "cats", "parameter_id": "species"}, {"text": " in "}, {"text": "Portland", "parameter_id": "location"}],
                [{"text": "I'm looking for a "}, {"text": "puppy", "parameter_id": "species"}],
                [{"text": "Search for pets in "}, {"text": "Boston", "parameter_id": "location"}],
                [{"text": "Find me a "}, {"text": "kitten", "parameter_id": "species"}],

                # Breed-specific dog searches
                [{"text": "I want to adopt a "}, {"text": "golden retriever", "parameter_id": "breed"}, {"text": " in "}, {"text": "Seattle", "parameter_id": "location"}],
                [{"text": "Looking for a "}, {"text": "labrador", "parameter_id": "breed"}, {"text": " near "}, {"text": "Portland", "parameter_id": "location"}],
                [{"text": "Show me "}, {"text": "german shepherd", "parameter_id": "breed"}, {"text": "s in "}, {"text": "Boston", "parameter_id": "location"}],
                [{"text": "I want a "}, {"text": "beagle", "parameter_id": "breed"}],
                [{"text": "Find me a "}, {"text": "corgi", "parameter_id": "breed"}, {"text": " in "}, {"text": "98101", "parameter_id": "location"}],
                [{"text": "I'm looking for a "}, {"text": "husky", "parameter_id": "breed"}],
                [{"text": "Show me "}, {"text": "poodle", "parameter_id": "breed"}, {"text": "s"}],
                [{"text": "I want to adopt a "}, {"text": "french bulldog", "parameter_id": "breed"}],

                # Breed-specific cat searches
                [{"text": "Looking for a "}, {"text": "siamese", "parameter_id": "breed"}, {"text": " cat in "}, {"text": "Seattle", "parameter_id": "location"}],
                [{"text": "I want a "}, {"text": "maine coon", "parameter_id": "breed"}],
                [{"text": "Show me "}, {"text": "persian", "parameter_id": "breed"}, {"text": " cats"}],
                [{"text": "I'm looking for a "}, {"text": "bengal", "parameter_id": "breed"}, {"text": " in "}, {"text": "Portland", "parameter_id": "location"}],
                [{"text": "Find me a "}, {"text": "ragdoll", "parameter_id": "breed"}],

                # Complex patterns with "I live in"
                [{"text": "I live in "}, {"text": "Seattle", "parameter_id": "location"}, {"text": " and want to adopt a "}, {"text": "dog", "parameter_id": "species"}],
                [{"text": "I live in "}, {"text": "Portland", "parameter_id": "location"}, {"text": " and I'm looking for a "}, {"text": "cat", "parameter_id": "species"}],
                [{"text": "I live in "}, {"text": "Boston", "parameter_id": "location"}, {"text": " looking for a "}, {"text": "puppy", "parameter_id": "species"}],
                [{"text": "I live in "}, {"text": "Seattle", "parameter_id": "location"}, {"text": " and want a "}, {"text": "golden retriever", "parameter_id": "breed"}],
                [{"text": "I live in "}, {"text": "Portland", "parameter_id": "location"}, {"text": " looking for a "}, {"text": "siamese", "parameter_id": "breed"}, {"text": " cat"}],

                # Complex sentences with extra details (train NLU to extract just location and species/breed)
                [{"text": "I live in "}, {"text": "Seattle", "parameter_id": "location"}, {"text": " and want to adopt a medium-sized "}, {"text": "dog", "parameter_id": "species"}, {"text": " that's good with cats"}],
                [{"text": "I'm in "}, {"text": "Portland", "parameter_id": "location"}, {"text": " looking for a friendly "}, {"text": "cat", "parameter_id": "species"}, {"text": " for my apartment"}],
                [{"text": "I live in "}, {"text": "Boston", "parameter_id": "location"}, {"text": " and need a "}, {"text": "dog", "parameter_id": "species"}, {"text": " suitable for apartment living"}],
                [{"text": "I live in "}, {"text": "Seattle", "parameter_id": "location"}, {"text": " and want a "}, {"text": "labrador", "parameter_id": "breed"}, {"text": " that's good with children"}],

                # Very complex sentences with multiple descriptors (like the actual user input)
                [{"text": "I live in "}, {"text": "Seattle", "parameter_id": "location"}, {"text": " and want to adopt a medium-sized "}, {"text": "dog", "parameter_id": "species"}, {"text": " that's good with cats and children"}],
                [{"text": "I live in "}, {"text": "Portland", "parameter_id": "location"}, {"text": " and want a "}, {"text": "dog", "parameter_id": "species"}, {"text": " suitable for apartment living and low-maintenance"}],
                [{"text": "I live in "}, {"text": "Boston", "parameter_id": "location"}, {"text": " and want to adopt a "}, {"text": "cat", "parameter_id": "species"}, {"text": " that's good with children, suitable for apartment living, and low-maintenance"}],
                [{"text": "I live in "}, {"text": "Seattle", "parameter_id": "location"}, {"text": " and want a medium-sized "}, {"text": "labrador", "parameter_id": "breed"}, {"text": " suitable for apartment living first-time owner"}],
                [{"text": "I'm in "}, {"text": "Portland", "parameter_id": "location"}, {"text": " looking for a friendly "}, {"text": "dog", "parameter_id": "species"}, {"text": " good with cats and children low-maintenance"}],
                [{"text": "I live in "}, {"text": "98101", "parameter_id": "location"}, {"text": " and want to adopt a "}, {"text": "dog", "parameter_id": "species"}, {"text": " that's suitable for apartment living low-maintenance first-time owner"}],

                # ZIP code patterns
                [{"text": "I want to adopt a "}, {"text": "dog", "parameter_id": "species"}, {"text": " near "}, {"text": "98101", "parameter_id": "location"}],
                [{"text": "Show me "}, {"text": "cats", "parameter_id": "species"}, {"text": " in zip code "}, {"text": "97201", "parameter_id": "location"}],
                [{"text": "Looking for a "}, {"text": "boxer", "parameter_id": "breed"}, {"text": " in "}, {"text": "98101", "parameter_id": "location"}],

                # Location-first patterns
                [{"text": "In "}, {"text": "Seattle", "parameter_id": "location"}, {"text": " I want to find a "}, {"text": "dog", "parameter_id": "species"}],
                [{"text": "Looking for a "}, {"text": "cat", "parameter_id": "species"}, {"text": " near "}, {"text": "Portland", "parameter_id": "location"}],
                [{"text": "In "}, {"text": "Boston", "parameter_id": "location"}, {"text": " show me "}, {"text": "beagle", "parameter_id": "breed"}, {"text": "s"}],

                # Generic search (no parameters)
                [{"text": "I want to search for a pet"}],
                [{"text": "Can you help me find a pet"}],
                [{"text": "Show me available pets"}],
                [{"text": "I'm looking for a pet to adopt"}]
            ],
            parameters=[
                {"id": "location", "entity_type": location_path},  # Use custom location entity
                {"id": "species", "entity_type": pet_species_path},  # Use custom pet_species entity
                {"id": "breed", "entity_type": dog_breed_path}  # Use @dog_breed (most common breed searches are dogs)
            ]
        )

        # intent.get_recommendations with affirmative responses and experience mentions
        self.get_or_create_intent(
            "intent.get_recommendations",
            [
                # Simple affirmatives
                [{"text": "Yes"}],
                [{"text": "Yes please"}],
                [{"text": "Show me recommendations"}],
                [{"text": "Yes please show me recommendations"}],
                [{"text": "Sure"}],
                [{"text": "Yes I'd like recommendations"}],
                [{"text": "That would be great"}],
                [{"text": "What pet would be good for me"}],
                [{"text": "Can you recommend a pet"}],
                [{"text": "Which pet should I adopt"}],
                [{"text": "Help me find the right pet"}],
                [{"text": "I don't know what pet to get"}],
                [{"text": "Recommend a pet for my lifestyle"}],
                [{"text": "Give me recommendations"}],
                [{"text": "I need help choosing a pet"}],

                # With experience mentioned (will be used to train NLU to recognize experience in complex sentences)
                [{"text": "Yes, I'm a first-time pet owner"}],
                [{"text": "Yes, I have experience with pets"}],
                [{"text": "Yes, I'm new to pets"}],
                [{"text": "Yes, I've owned pets before"}],
                [{"text": "Yes, I'm experienced with dogs"}],
                [{"text": "Sure, I've never had a pet before"}]
            ]
        )

        # Other intents
        self.get_or_create_intent(
            "intent.schedule_visit",
            [
                # Affirmative responses (from Pet Details page)
                [{"text": "Yes schedule a visit"}],
                [{"text": "Yes"}],
                [{"text": "Sure, schedule a visit"}],
                [{"text": "Yes please"}],
                [{"text": "That sounds good"}],
                [{"text": "Let's do that"}],
                [{"text": "Schedule a visit"}],

                # Direct requests
                [{"text": "I want to schedule a visit"}],
                [{"text": "Can I meet the pet"}],
                [{"text": "Schedule a time to see the pet"}],
                [{"text": "I'd like to visit the shelter"}],
                [{"text": "Book a visit"}],
                [{"text": "Set up an appointment"}],
                [{"text": "I want to visit"}],
                [{"text": "Make an appointment"}],
                [{"text": "Can I come see the pet"}],
                [{"text": "I'd like to meet the pet"}]
            ]
        )

        self.get_or_create_intent(
            "intent.adoption_application",
            [
                [{"text": "I want to adopt"}],
                [{"text": "Start adoption application"}],
                [{"text": "Apply to adopt this pet"}],
                [{"text": "I'd like to adopt"}],
                [{"text": "Begin adoption process"}],
                [{"text": "Submit adoption application"}]
            ]
        )

        self.get_or_create_intent(
            "intent.foster_application",
            [
                [{"text": "I want to foster"}],
                [{"text": "Start foster application"}],
                [{"text": "Apply to foster this pet"}],
                [{"text": "I'd like to foster"}],
                [{"text": "Can I foster temporarily"}]
            ]
        )

        self.get_or_create_intent(
            "intent.search_more",
            [
                [{"text": "Show me more pets"}],
                [{"text": "Search again"}],
                [{"text": "Find other pets"}],
                [{"text": "Look for different pets"}],
                [{"text": "Start a new search"}]
            ]
        )

        self.get_or_create_intent(
            "intent.ask_question",
            [
                [{"text": "Tell me about Golden Retrievers"}],
                [{"text": "What do I need to know about cats"}],
                [{"text": "How much exercise does a dog need"}],
                [{"text": "What should I prepare before adopting"}],
                [{"text": "What's the adoption process"}]
            ]
        )

        # intent.ask_pet_question - asks questions about the current pet in context
        self.get_or_create_intent(
            "intent.ask_pet_question",
            [
                # Medical/health questions with names
                [{"text": "Does "}, {"text": "Lucky", "parameter_id": "pet_name"}, {"text": " have medical issues"}],
                [{"text": "Does "}, {"text": "Lucky", "parameter_id": "pet_name"}, {"text": " have any health problems"}],
                [{"text": "Is "}, {"text": "Lucky", "parameter_id": "pet_name"}, {"text": " healthy"}],

                # Medical/health questions with pronouns
                [{"text": "Does she have medical issues"}],
                [{"text": "Does he have medical issues"}],
                [{"text": "Does she have any health problems"}],
                [{"text": "Does he have any health problems"}],
                [{"text": "Is she healthy"}],
                [{"text": "Is he healthy"}],
                [{"text": "Does this pet have medical issues"}],
                [{"text": "Are there any health concerns"}],
                [{"text": "What are the medical conditions"}],
                [{"text": "Does the pet need special care"}],
                [{"text": "Any health issues I should know about"}],

                # Behavior questions with names
                [{"text": "Is "}, {"text": "Lucky", "parameter_id": "pet_name"}, {"text": " good with kids"}],
                [{"text": "Is "}, {"text": "Lucky", "parameter_id": "pet_name"}, {"text": " good with other dogs"}],
                [{"text": "Is "}, {"text": "Lucky", "parameter_id": "pet_name"}, {"text": " good with cats"}],
                [{"text": "Does "}, {"text": "Rosie", "parameter_id": "pet_name"}, {"text": " like to go on walks"}],

                # Behavior questions with pronouns
                [{"text": "Is she good with kids"}],
                [{"text": "Is he good with kids"}],
                [{"text": "Is she good with other dogs"}],
                [{"text": "Is he good with other dogs"}],
                [{"text": "Is she good with cats"}],
                [{"text": "Is he good with cats"}],
                [{"text": "Does she like to go on walks"}],
                [{"text": "Does he like to go on walks"}],
                [{"text": "Does she like walks"}],
                [{"text": "Does he like walks"}],
                [{"text": "Does this pet get along with children"}],
                [{"text": "Is the pet house trained"}],
                [{"text": "How is the pet with other animals"}],
                [{"text": "What's the pet's temperament"}],
                [{"text": "Is the pet friendly"}],
                [{"text": "Is she friendly"}],
                [{"text": "Is he friendly"}],

                # Care requirements with pronouns
                [{"text": "How much exercise does "}, {"text": "Lucky", "parameter_id": "pet_name"}, {"text": " need"}],
                [{"text": "How much exercise does she need"}],
                [{"text": "How much exercise does he need"}],
                [{"text": "What are the grooming needs"}],
                [{"text": "Does the pet need a fenced yard"}],
                [{"text": "Does she need a fenced yard"}],
                [{"text": "Does he need a fenced yard"}],
                [{"text": "What kind of home does this pet need"}],
                [{"text": "Is this pet suitable for apartments"}],
                [{"text": "Is she suitable for apartments"}],
                [{"text": "Is he suitable for apartments"}],

                # General questions
                [{"text": "Tell me more about "}, {"text": "Lucky", "parameter_id": "pet_name"}],
                [{"text": "What else should I know about "}, {"text": "Lucky", "parameter_id": "pet_name"}],
                [{"text": "Can you tell me more about this pet"}],
                [{"text": "Tell me more about her"}],
                [{"text": "Tell me more about him"}],
                [{"text": "What else should I know about her"}],
                [{"text": "What else should I know about him"}],
                [{"text": "What's the pet's story"}],
                [{"text": "Why is this pet up for adoption"}]
            ],
            parameters=[
                {"id": "pet_name", "entity_type": "projects/-/locations/-/agents/-/entityTypes/sys.any"}
            ]
        )

        # intent.get_pet_details - captures requests for specific pet information
        self.get_or_create_intent(
            "intent.get_pet_details",
            [
                # By pet name
                [{"text": "Tell me more about "}, {"text": "Lucky", "parameter_id": "pet_id"}],
                [{"text": "Tell me about "}, {"text": "Rosie", "parameter_id": "pet_id"}],
                [{"text": "I want to know more about "}, {"text": "Gabino", "parameter_id": "pet_id"}],
                [{"text": "Show me more about "}, {"text": "Sponsor Joe", "parameter_id": "pet_id"}],
                [{"text": "More information about "}, {"text": "Lucky", "parameter_id": "pet_id"}],
                [{"text": "Can I learn more about "}, {"text": "Rosie", "parameter_id": "pet_id"}],
                [{"text": "What about "}, {"text": "Gabino", "parameter_id": "pet_id"}],
                [{"text": "Tell me about the "}, {"text": "Labrador", "parameter_id": "pet_id"}],
                [{"text": "More about "}, {"text": "Lucky", "parameter_id": "pet_id"}],
                [{"text": "Info on "}, {"text": "Rosie", "parameter_id": "pet_id"}],
                [{"text": "Details about "}, {"text": "Lucky", "parameter_id": "pet_id"}],

                # By pet ID
                [{"text": "Tell me about pet "}, {"text": "10244680", "parameter_id": "pet_id"}],
                [{"text": "Show me pet "}, {"text": "10353561", "parameter_id": "pet_id"}],
                [{"text": "I want to know about "}, {"text": "10399685", "parameter_id": "pet_id"}],
                [{"text": "More info on "}, {"text": "10244680", "parameter_id": "pet_id"}],
                [{"text": "Details for "}, {"text": "10353561", "parameter_id": "pet_id"}],
                [{"text": "Tell me more about ID "}, {"text": "10244680", "parameter_id": "pet_id"}],
                [{"text": "Show me ID "}, {"text": "10399685", "parameter_id": "pet_id"}],

                # Mixed patterns
                [{"text": "More about pet "}, {"text": "Lucky", "parameter_id": "pet_id"}],
                [{"text": "I'd like to know more about "}, {"text": "10244680", "parameter_id": "pet_id"}],
                [{"text": "Can you tell me about "}, {"text": "Rosie", "parameter_id": "pet_id"}],
                [{"text": "What can you tell me about "}, {"text": "Gabino", "parameter_id": "pet_id"}],

                # Simple patterns (just the name/ID)
                [{"text": "Lucky"}],
                [{"text": "10244680"}],
                [{"text": "Rosie"}],
                [{"text": "Pet "}, {"text": "10353561", "parameter_id": "pet_id"}]
            ],
            parameters=[
                {"id": "pet_id", "entity_type": sys_any}
            ]
        )

        logger.info("✓ Intents configured")

    def setup_webhook(self) -> Optional[str]:
        """Create/update webhook if URL provided."""
        if not self.webhook_url:
            logger.info("No webhook URL provided, skipping webhook setup")
            return None

        logger.info(f"Setting up webhook: {self.webhook_url}")

        # Try to find existing webhook
        webhooks_list = list(self.webhooks_client.list_webhooks(parent=self.agent_path))
        for webhook in webhooks_list:
            if webhook.display_name == "PawConnect Webhook":
                logger.info("  Found existing webhook, updating...")
                webhook.generic_web_service.uri = self.webhook_url
                updated = self.webhooks_client.update_webhook(webhook=webhook)
                logger.info("  ✓ Webhook updated")
                return updated.name

        # Create new
        logger.info("  Creating new webhook...")
        webhook = Webhook(
            display_name="PawConnect Webhook",
            generic_web_service=Webhook.GenericWebService(uri=self.webhook_url),
            timeout=field_mask_pb2.Duration(seconds=30)
        )
        created = self.webhooks_client.create_webhook(
            parent=self.agent_path,
            webhook=webhook
        )
        logger.info("  ✓ Webhook created")
        return created.name

    def setup_flows_and_pages(self, webhook_name: Optional[str] = None):
        """Set up flows, pages, and transition routes."""
        logger.info("Setting up flows and pages...")

        # Get default flow
        flows_list = list(self.flows_client.list_flows(parent=self.agent_path))
        default_flow = next((f for f in flows_list if f.display_name == "Default Start Flow"), None)

        if not default_flow:
            logger.error("Default Start Flow not found")
            return

        flow_name = default_flow.name
        logger.info(f"  Using flow: {flow_name}")

        # Get intents first (needed for routes)
        intent_search_pets = self._intents_cache.get("intent.search_pets")
        intent_get_recommendations = self._intents_cache.get("intent.get_recommendations")
        intent_get_pet_details = self._intents_cache.get("intent.get_pet_details")
        intent_ask_pet_question = self._intents_cache.get("intent.ask_pet_question")

        if not intent_search_pets or not intent_get_recommendations:
            logger.warning("  Intents not found in cache, skipping page configuration")
            return

        # List all pages in the flow
        pages_list = list(self.pages_client.list_pages(parent=flow_name))
        pages_by_name = {p.display_name: p for p in pages_list}

        # Debug: Log all page names
        logger.info(f"  Found {len(pages_list)} pages: {[p.display_name for p in pages_list]}")

        # Find START_PAGE - try different possible names
        start_page = None
        for page in pages_list:
            if page.display_name in ["START_PAGE", "Start Page", "start_page"]:
                start_page = page
                logger.info(f"  Found START_PAGE: {page.name}")
                break

        # If not found in list, try to access START_PAGE directly with special ID
        if not start_page:
            try:
                # START_PAGE has a special UUID of all zeros
                start_page_path = f"{flow_name}/pages/00000000-0000-0000-0000-000000000000"
                logger.info(f"  Attempting to access START_PAGE directly: {start_page_path}")
                start_page = self.pages_client.get_page(name=start_page_path)
                logger.info("  ✓ Successfully accessed START_PAGE directly!")
            except Exception as e:
                logger.info(f"  Could not access START_PAGE directly: {e}")
                start_page = None

        # CRITICAL FIX: Update the problematic sys.no-match-default event handler at flow level
        # Instead of deleting (which API won't allow), we'll update it with a better message
        try:
            flow = self.flows_client.get_flow(name=flow_name)

            # Find and update sys.no-match-default handlers that have the welcome message
            updated = False
            for eh in flow.event_handlers:
                if eh.event == "sys.no-match-default":
                    # Check if this handler has the welcome message
                    has_welcome = any(
                        "Welcome to PawConnect" in text
                        for msg in eh.trigger_fulfillment.messages
                        for text in (msg.text.text if hasattr(msg, 'text') else [])
                    )

                    if has_welcome:
                        # Update with a more appropriate message for no-match scenarios
                        eh.trigger_fulfillment.messages[:] = [
                            ResponseMessage(
                                text=ResponseMessage.Text(
                                    text=["I didn't quite catch that. Could you rephrase or try again?"]
                                )
                            )
                        ]
                        updated = True
                        logger.info("  ✓ Updated sys.no-match-default event handler with appropriate message")

            if updated:
                # Update the flow
                update_mask = {"paths": ["event_handlers"]}
                self.flows_client.update_flow(flow=flow, update_mask=update_mask)
            else:
                logger.info("  No problematic event handlers found to update")
        except Exception as e:
            logger.warning(f"  Could not update flow event handlers: {e}")

        # Configure START_PAGE if we found it
        if not start_page:
            logger.info("  START_PAGE not accessible, will configure routes at flow level...")
            # We'll skip the welcome message configuration and just set up routes at flow level
            # The welcome message can be configured manually in the Dialogflow Console if needed
        else:
            # Update START_PAGE with welcome message
            logger.info("  Configuring welcome message on START_PAGE...")
            welcome_message = (
                "Welcome to PawConnect! I'm here to help you find your perfect pet companion. "
                "I can help you search for pets, learn about specific animals, schedule visits, "
                "or start an adoption application. What would you like to do?"
            )

            start_page.entry_fulfillment = Fulfillment(
                messages=[
                    ResponseMessage(
                        text=ResponseMessage.Text(text=[welcome_message])
                    )
                ]
            )

            self.pages_client.update_page(page=start_page)
            logger.info("  ✓ Welcome message configured")

        # Pet Search page
        if "Pet Search" not in pages_by_name:
            logger.info("  Creating Pet Search page...")

            # Get custom entity types for page creation
            pet_species_entity = self._entity_types_cache.get("pet_species")
            pet_species_path = pet_species_entity.name if pet_species_entity else "projects/-/locations/-/agents/-/entityTypes/sys.any"

            dog_breed_entity = self._entity_types_cache.get("dog_breed")
            dog_breed_path = dog_breed_entity.name if dog_breed_entity else "projects/-/locations/-/agents/-/entityTypes/sys.any"

            location_entity = self._entity_types_cache.get("location")
            location_path = location_entity.name if location_entity else "projects/-/locations/-/agents/-/entityTypes/sys.location"

            pet_search_page = self.pages_client.create_page(
                parent=flow_name,
                page=Page(
                    display_name="Pet Search",
                    form=Form(
                        parameters=[
                            Form.Parameter(
                                display_name="location",
                                entity_type=location_path,
                                required=True,
                                fill_behavior=Form.Parameter.FillBehavior(
                                    initial_prompt_fulfillment=Fulfillment(
                                        messages=[ResponseMessage(text=ResponseMessage.Text(text=["Where are you located?"]))]
                                    )
                                )
                            ),
                            Form.Parameter(
                                display_name="species",
                                entity_type=pet_species_path,
                                required=False,  # Optional since user might specify breed
                                fill_behavior=Form.Parameter.FillBehavior(
                                    initial_prompt_fulfillment=Fulfillment(
                                        messages=[ResponseMessage(text=ResponseMessage.Text(text=["What type of pet are you looking for? (dog, cat, etc.)"]))]
                                    )
                                )
                            ),
                            Form.Parameter(
                                display_name="breed",
                                entity_type=dog_breed_path,
                                required=False,
                                fill_behavior=Form.Parameter.FillBehavior(
                                    initial_prompt_fulfillment=Fulfillment(
                                        messages=[ResponseMessage(text=ResponseMessage.Text(text=["Any specific breed in mind? (optional)"]))]
                                    )
                                )
                            )
                        ]
                    ),
                    transition_routes=[
                        TransitionRoute(
                            condition="$page.params.status = \"FINAL\"",
                            trigger_fulfillment=Fulfillment(
                                webhook=webhook_name,
                                tag="search-pets"
                            ) if webhook_name else Fulfillment(
                                messages=[ResponseMessage(text=ResponseMessage.Text(text=["Searching for pets..."]))]
                            )
                            # No target specified - let webhook response control the flow
                        )
                    ]
                )
            )
            logger.info("  ✓ Pet Search page created with location (@sys.location), species (@pet_species), breed (@dog_breed)")
        else:
            # Update existing page to ensure webhook route is configured
            logger.info("  Updating Pet Search page with form parameters and webhook route...")
            old_page = pages_by_name["Pet Search"]

            # Get custom entity types
            pet_species_entity = self._entity_types_cache.get("pet_species")
            pet_species_path = pet_species_entity.name if pet_species_entity else "projects/-/locations/-/agents/-/entityTypes/sys.any"

            dog_breed_entity = self._entity_types_cache.get("dog_breed")
            dog_breed_path = dog_breed_entity.name if dog_breed_entity else "projects/-/locations/-/agents/-/entityTypes/sys.any"

            location_entity = self._entity_types_cache.get("location")
            location_path = location_entity.name if location_entity else "projects/-/locations/-/agents/-/entityTypes/sys.location"

            # Create a brand new Page object with all the configuration
            # This avoids protobuf nested type issues when modifying existing objects
            pet_search_page = Page(
                name=old_page.name,  # Preserve the page path so API knows which page to update
                display_name="Pet Search",
                form=Form(
                    parameters=[
                        Form.Parameter(
                            display_name="location",
                            entity_type=location_path,
                            required=True,
                            fill_behavior=Form.Parameter.FillBehavior(
                                initial_prompt_fulfillment=Fulfillment(
                                    messages=[ResponseMessage(text=ResponseMessage.Text(text=["Where are you located?"]))]
                                )
                            )
                        ),
                        Form.Parameter(
                            display_name="species",
                            entity_type=pet_species_path,
                            required=False,  # Optional since user might specify breed instead
                            fill_behavior=Form.Parameter.FillBehavior(
                                initial_prompt_fulfillment=Fulfillment(
                                    messages=[ResponseMessage(text=ResponseMessage.Text(text=["What type of pet are you looking for? (dog, cat, etc.)"]))]
                                )
                            )
                        ),
                        Form.Parameter(
                            display_name="breed",
                            entity_type=dog_breed_path,
                            required=False,
                            fill_behavior=Form.Parameter.FillBehavior(
                                initial_prompt_fulfillment=Fulfillment(
                                    messages=[ResponseMessage(text=ResponseMessage.Text(text=["Any specific breed in mind? (optional)"]))]
                                )
                            )
                        )
                    ]
                ),
                entry_fulfillment=Fulfillment(),  # Clear to prevent double webhook calls
                transition_routes=[
                    TransitionRoute(
                        condition="$page.params.status = \"FINAL\"",
                        trigger_fulfillment=Fulfillment(
                            webhook=webhook_name,
                            tag="search-pets"
                        ) if webhook_name else Fulfillment(
                            messages=[ResponseMessage(text=ResponseMessage.Text(text=["Searching for pets..."]))]
                        )
                    )
                ]
            )
            logger.info("  Created new Page object with form parameters and webhook route")

            # Update the page
            self.pages_client.update_page(page=pet_search_page)
            logger.info("  ✓ Pet Search page updated (form parameters, cleared entry fulfillment, set webhook route)")

        # Get Recommendations page
        # Get housing_type entity
        housing_entity = self._entity_types_cache.get("housing_type")
        housing_entity_path = housing_entity.name if housing_entity else "projects/-/locations/-/agents/-/entityTypes/sys.any"

        logger.info(f"  Using housing_type entity: {housing_entity_path}")

        if "Get Recommendations" not in pages_by_name:
            logger.info("  Creating Get Recommendations page...")

            get_rec_page = self.pages_client.create_page(
                parent=flow_name,
                page=Page(
                    display_name="Get Recommendations",
                    form=Form(
                        parameters=[
                            Form.Parameter(
                                display_name="housing",
                                entity_type=housing_entity_path,
                                required=True,
                                fill_behavior=Form.Parameter.FillBehavior(
                                    initial_prompt_fulfillment=Fulfillment(
                                        messages=[ResponseMessage(text=ResponseMessage.Text(text=["What type of housing do you have? (apartment, house, condo, etc.)"]))]
                                    )
                                )
                            ),
                            Form.Parameter(
                                display_name="experience",
                                entity_type="projects/-/locations/-/agents/-/entityTypes/sys.any",
                                required=True,
                                fill_behavior=Form.Parameter.FillBehavior(
                                    initial_prompt_fulfillment=Fulfillment(
                                        messages=[ResponseMessage(text=ResponseMessage.Text(text=["Do you have experience with pets?"]))]
                                    )
                                )
                            )
                        ]
                    ),
                    transition_routes=[
                        TransitionRoute(
                            condition="$page.params.status = \"FINAL\"",
                            trigger_fulfillment=Fulfillment(
                                webhook=webhook_name,
                                tag="get-recommendations"
                            ) if webhook_name else Fulfillment(
                                messages=[ResponseMessage(text=ResponseMessage.Text(text=["Getting recommendations..."]))]
                            )
                            # No target specified - let webhook response control the flow
                        )
                    ]
                )
            )
            logger.info("  ✓ Get Recommendations page created")
        else:
            # Update existing page to ensure correct entity type and transition routes
            logger.info("  Updating Get Recommendations page with correct entity type...")
            get_rec_page = pages_by_name["Get Recommendations"]

            # Update the form parameters with correct entity types and prompts
            # Configure housing parameter
            housing_param = get_rec_page.form.parameters[0]
            housing_param.entity_type = housing_entity_path
            housing_param.display_name = "housing"
            housing_param.required = True
            # Update the fill_behavior prompt
            housing_param.fill_behavior.initial_prompt_fulfillment.messages[:] = [
                ResponseMessage(text=ResponseMessage.Text(
                    text=["What type of housing do you have? (apartment, house, condo, etc.)"]
                ))
            ]

            # Configure experience parameter if it exists
            if len(get_rec_page.form.parameters) >= 2:
                experience_param = get_rec_page.form.parameters[1]
                # Get experience_level entity from cache
                experience_level_entity = self._entity_types_cache.get("experience_level")
                experience_level_path = experience_level_entity.name if experience_level_entity else "projects/-/locations/-/agents/-/entityTypes/sys.any"
                experience_param.entity_type = experience_level_path
                experience_param.display_name = "experience"
                experience_param.required = True
                # Update the fill_behavior prompt
                experience_param.fill_behavior.initial_prompt_fulfillment.messages[:] = [
                    ResponseMessage(text=ResponseMessage.Text(
                        text=["Do you have experience with pets?"]
                    ))
                ]

            # Clear entry_fulfillment to prevent double webhook calls
            # The webhook should ONLY be called when form is complete, not when entering the page
            get_rec_page.entry_fulfillment = Fulfillment()

            # CRITICAL: Clear all page-level event handlers
            # These can interfere with transition routes and cause loops
            event_handler_count = len(get_rec_page.event_handlers)
            get_rec_page.event_handlers.clear()
            if event_handler_count > 0:
                logger.info(f"  Cleared {event_handler_count} page-level event handler(s)")

            # Update transition routes to ensure webhook is called when form is complete
            get_rec_page.transition_routes.clear()
            get_rec_page.transition_routes.append(
                TransitionRoute(
                    condition="$page.params.status = \"FINAL\"",
                    trigger_fulfillment=Fulfillment(
                        webhook=webhook_name,
                        tag="get-recommendations"
                    ) if webhook_name else Fulfillment(
                        messages=[ResponseMessage(text=ResponseMessage.Text(text=["Getting recommendations..."]))]
                    )
                    # No target specified - let webhook response control the flow
                )
            )

            # Update the page
            self.pages_client.update_page(page=get_rec_page)
            logger.info("  ✓ Get Recommendations page updated (cleared entry fulfillment, set webhook route)")

        # Pet Details page
        if "Pet Details" not in pages_by_name:
            logger.info("  Creating Pet Details page...")

            pet_details_page = self.pages_client.create_page(
                parent=flow_name,
                page=Page(
                    display_name="Pet Details",
                    form=Form(
                        parameters=[
                            Form.Parameter(
                                display_name="pet_id",
                                entity_type="projects/-/locations/-/agents/-/entityTypes/sys.any",
                                required=True,
                                fill_behavior=Form.Parameter.FillBehavior(
                                    initial_prompt_fulfillment=Fulfillment(
                                        messages=[ResponseMessage(text=ResponseMessage.Text(
                                            text=["Which pet would you like to know more about? Please provide the pet's name or ID number."]
                                        ))]
                                    )
                                )
                            )
                        ]
                    ),
                    transition_routes=[
                        TransitionRoute(
                            condition="$page.params.status = \"FINAL\"",
                            trigger_fulfillment=Fulfillment(
                                webhook=webhook_name,
                                tag="validate-pet-id"
                            ) if webhook_name else Fulfillment(
                                messages=[ResponseMessage(text=ResponseMessage.Text(text=["Looking up pet details..."]))]
                            )
                            # No target specified - let webhook response control the flow
                        )
                    ]
                )
            )
            logger.info("  ✓ Pet Details page created with pet_id parameter and validate-pet-id webhook")
        else:
            # Update existing page to ensure webhook route is configured
            logger.info("  Updating Pet Details page - adding session tracking to prevent double responses...")
            pet_details_page = pages_by_name["Pet Details"]

            # Create a brand new Page object with all the configuration
            # Use session parameter to track if pet details were already loaded
            pet_details_page = Page(
                name=pet_details_page.name,  # Preserve the page path
                display_name="Pet Details",
                form=Form(
                    parameters=[
                        Form.Parameter(
                            display_name="pet_id",
                            entity_type="projects/-/locations/-/agents/-/entityTypes/sys.any",
                            required=True,
                            fill_behavior=Form.Parameter.FillBehavior(
                                initial_prompt_fulfillment=Fulfillment(
                                    messages=[ResponseMessage(text=ResponseMessage.Text(
                                        text=["Which pet would you like to know more about? Please provide the pet's name or ID number."]
                                    ))]
                                )
                            )
                        )
                    ]
                ),
                entry_fulfillment=Fulfillment(),  # Clear to prevent double webhook calls
                transition_routes=[
                    TransitionRoute(
                        # Only trigger on FINAL if we haven't already loaded details for this pet
                        condition='$page.params.status = "FINAL" AND ($session.params.current_pet_id != $page.params.pet_id OR NOT $session.params.pet_details_loaded)',
                        trigger_fulfillment=Fulfillment(
                            webhook=webhook_name,
                            tag="validate-pet-id"
                        ) if webhook_name else Fulfillment(
                            messages=[ResponseMessage(text=ResponseMessage.Text(text=["Looking up pet details..."]))]
                        )
                    )
                ]
            )

            # Update the page
            self.pages_client.update_page(page=pet_details_page)
            logger.info("  ✓ Pet Details page updated (session tracking to prevent re-firing)")

        # Schedule Visit page
        if "Schedule Visit" not in pages_by_name:
            logger.info("  Creating Schedule Visit page...")

            schedule_visit_page = self.pages_client.create_page(
                parent=flow_name,
                page=Page(
                    display_name="Schedule Visit",
                    form=Form(
                        parameters=[
                            Form.Parameter(
                                display_name="date",
                                entity_type="projects/-/locations/-/agents/-/entityTypes/sys.date",
                                required=True,
                                fill_behavior=Form.Parameter.FillBehavior(
                                    initial_prompt_fulfillment=Fulfillment(
                                        messages=[ResponseMessage(text=ResponseMessage.Text(
                                            text=["What date would you like to visit?"]
                                        ))]
                                    )
                                )
                            ),
                            Form.Parameter(
                                display_name="time",
                                entity_type="projects/-/locations/-/agents/-/entityTypes/sys.time",
                                required=True,
                                fill_behavior=Form.Parameter.FillBehavior(
                                    initial_prompt_fulfillment=Fulfillment(
                                        messages=[ResponseMessage(text=ResponseMessage.Text(
                                            text=["What time works best for you?"]
                                        ))]
                                    )
                                )
                            )
                        ]
                    ),
                    transition_routes=[
                        TransitionRoute(
                            condition="$page.params.status = \"FINAL\"",
                            trigger_fulfillment=Fulfillment(
                                webhook=webhook_name,
                                tag="schedule-visit"
                            ) if webhook_name else Fulfillment(
                                messages=[ResponseMessage(text=ResponseMessage.Text(text=["Scheduling your visit..."]))]
                            )
                            # No target specified - let webhook response control the flow
                        )
                    ]
                )
            )
            logger.info("  ✓ Schedule Visit page created with date and time parameters")
        else:
            # Update existing page
            logger.info("  Updating Schedule Visit page...")
            schedule_visit_page = pages_by_name["Schedule Visit"]

            schedule_visit_page = Page(
                name=schedule_visit_page.name,
                display_name="Schedule Visit",
                form=Form(
                    parameters=[
                        Form.Parameter(
                            display_name="date",
                            entity_type="projects/-/locations/-/agents/-/entityTypes/sys.date",
                            required=True,
                            fill_behavior=Form.Parameter.FillBehavior(
                                initial_prompt_fulfillment=Fulfillment(
                                    messages=[ResponseMessage(text=ResponseMessage.Text(
                                        text=["What date would you like to visit?"]
                                    ))]
                                )
                            )
                        ),
                        Form.Parameter(
                            display_name="time",
                            entity_type="projects/-/locations/-/agents/-/entityTypes/sys.time",
                            required=True,
                            fill_behavior=Form.Parameter.FillBehavior(
                                initial_prompt_fulfillment=Fulfillment(
                                    messages=[ResponseMessage(text=ResponseMessage.Text(
                                        text=["What time works best for you?"]
                                    ))]
                                )
                            )
                        )
                    ]
                ),
                entry_fulfillment=Fulfillment(),
                transition_routes=[
                    TransitionRoute(
                        condition="$page.params.status = \"FINAL\"",
                        trigger_fulfillment=Fulfillment(
                            webhook=webhook_name,
                            tag="schedule-visit"
                        ) if webhook_name else Fulfillment(
                            messages=[ResponseMessage(text=ResponseMessage.Text(text=["Scheduling your visit..."]))]
                        )
                    )
                ]
            )

            self.pages_client.update_page(page=schedule_visit_page)
            logger.info("  ✓ Schedule Visit page updated")

        # Now update Pet Details page to add transition routes
        logger.info("  Adding transition routes to Pet Details page...")
        pages_list = list(self.pages_client.list_pages(parent=flow_name))
        pet_details_page = next((p for p in pages_list if p.display_name == "Pet Details"), None)
        schedule_visit_page = next((p for p in pages_list if p.display_name == "Schedule Visit"), None)
        intent_schedule_visit = self._intents_cache.get("intent.schedule_visit")
        intent_ask_pet_question = self._intents_cache.get("intent.ask_pet_question")

        if pet_details_page and intent_schedule_visit:
            # Get the current page
            pet_details_full = self.pages_client.get_page(name=pet_details_page.name)

            # Add intent-based transition routes (these run AFTER webhook completes)
            # Clear existing intent routes to avoid duplicates
            existing_routes = [r for r in pet_details_full.transition_routes if not r.intent]

            # Add our new routes
            new_routes = []

            # Add schedule visit route
            if schedule_visit_page:
                new_routes.append(
                    TransitionRoute(
                        intent=intent_schedule_visit.name,
                        target_page=schedule_visit_page.name
                    )
                )

            # Add ask pet question route (stays on Pet Details page, calls webhook)
            if intent_ask_pet_question:
                new_routes.append(
                    TransitionRoute(
                        intent=intent_ask_pet_question.name,
                        trigger_fulfillment=Fulfillment(
                            webhook=webhook_name,
                            tag="ask-pet-question"
                        ) if webhook_name else Fulfillment(
                            messages=[ResponseMessage(text=ResponseMessage.Text(text=["Let me look that up for you..."]))]
                        )
                        # No target page - stay on Pet Details page
                    )
                )

            pet_details_full.transition_routes.clear()
            pet_details_full.transition_routes.extend(existing_routes + new_routes)

            self.pages_client.update_page(page=pet_details_full)
            logger.info("  ✓ Added routes: Pet Details -> (intent.schedule_visit) -> Schedule Visit")
            if intent_ask_pet_question:
                logger.info("  ✓ Added route: Pet Details -> (intent.ask_pet_question) -> webhook -> stay on page")

        # Add transition routes to START_PAGE
        if start_page:
            logger.info("  Configuring START_PAGE transition routes...")

            # Refresh pages list to get newly created pages
            pages_list = list(self.pages_client.list_pages(parent=flow_name))
            pet_search_page = next((p for p in pages_list if p.display_name == "Pet Search"), None)
            get_rec_page = next((p for p in pages_list if p.display_name == "Get Recommendations"), None)
            pet_details_page = next((p for p in pages_list if p.display_name == "Pet Details"), None)

            if pet_search_page and get_rec_page:
                start_page.transition_routes.clear()
                routes = [
                    TransitionRoute(
                        intent=intent_search_pets.name,
                        trigger_fulfillment=Fulfillment(
                            webhook=webhook_name,
                            tag="search-pets"
                        )
                        # Call webhook directly with intent parameters
                    ),
                    TransitionRoute(
                        intent=intent_get_recommendations.name,
                        target_page=get_rec_page.name
                    )
                ]

                # Add pet details route if intent and page exist
                if intent_get_pet_details and pet_details_page:
                    routes.append(
                        TransitionRoute(
                            intent=intent_get_pet_details.name,
                            target_page=pet_details_page.name
                        )
                    )
                    logger.info("  Added route for intent.get_pet_details -> Pet Details page")

                start_page.transition_routes.extend(routes)

                self.pages_client.update_page(page=start_page)
                logger.info("  ✓ Transition routes configured")
        else:
            # If START_PAGE not found, add routes to flow level
            logger.info("  Configuring transition routes at flow level...")

            # Refresh pages list to get newly created pages
            pages_list = list(self.pages_client.list_pages(parent=flow_name))
            pet_search_page = next((p for p in pages_list if p.display_name == "Pet Search"), None)
            get_rec_page = next((p for p in pages_list if p.display_name == "Get Recommendations"), None)
            pet_details_page = next((p for p in pages_list if p.display_name == "Pet Details"), None)

            if pet_search_page and get_rec_page:
                # Get the flow and add transition routes
                flow = self.flows_client.get_flow(name=flow_name)

                # Keep existing routes but filter out our intents first to avoid duplicates
                our_intents = [intent_search_pets.name, intent_get_recommendations.name]
                if intent_get_pet_details:
                    our_intents.append(intent_get_pet_details.name)

                existing_routes = [
                    route for route in flow.transition_routes
                    if route.intent not in our_intents
                ]

                # Add our routes
                new_routes = [
                    TransitionRoute(
                        intent=intent_search_pets.name,
                        trigger_fulfillment=Fulfillment(
                            webhook=webhook_name,
                            tag="search-pets"
                        )
                        # Call webhook directly with intent parameters
                    ),
                    TransitionRoute(
                        intent=intent_get_recommendations.name,
                        target_page=get_rec_page.name
                    )
                ]

                # Add pet details route if intent and page exist
                if intent_get_pet_details and pet_details_page:
                    new_routes.append(
                        TransitionRoute(
                            intent=intent_get_pet_details.name,
                            target_page=pet_details_page.name
                        )
                    )
                    logger.info("  Added flow-level route for intent.get_pet_details -> Pet Details page")

                # Update flow with combined routes
                flow.transition_routes.clear()
                flow.transition_routes.extend(existing_routes + new_routes)

                self.flows_client.update_flow(flow=flow)
                logger.info("  ✓ Transition routes configured at flow level")

        logger.info("✓ Flows and pages configured")

    def run_complete_setup(self):
        """Run complete setup."""
        try:
            logger.info(f"Setting up agent: {self.agent_path}")
            logger.info("")

            self.setup_entity_types()
            logger.info("")

            self.setup_intents()
            logger.info("")

            webhook_name = self.setup_webhook()
            logger.info("")

            self.setup_flows_and_pages(webhook_name)
            logger.info("")

            return True
        except Exception as e:
            logger.error(f"Setup failed: {e}")
            import traceback
            traceback.print_exc()
            return False


def find_agent(project_id: str, location: str = "us-central1") -> Optional[str]:
    """Find agent ID automatically."""
    try:
        parent = f"projects/{project_id}/locations/{location}"
        api_endpoint = f"{location}-dialogflow.googleapis.com"
        client_options = ClientOptions(api_endpoint=api_endpoint)
        agents_client = AgentsClient(client_options=client_options)

        agents = list(agents_client.list_agents(parent=parent))
        if agents:
            agent_id = agents[0].name.split("/")[-1]
            logger.info(f"Auto-detected agent: {agents[0].display_name} ({agent_id})")
            return agent_id
        else:
            logger.error("No agents found in project")
            return None
    except Exception as e:
        logger.error(f"Failed to find agent: {e}")
        return None


def main():
    """Main entry point."""
    import argparse

    # Get defaults from environment variables
    default_project_id = os.getenv("GCP_PROJECT_ID")
    default_agent_id = os.getenv("DIALOGFLOW_AGENT_ID")
    default_location = os.getenv("DIALOGFLOW_LOCATION", "us-central1")
    default_webhook_url = os.getenv("DIALOGFLOW_WEBHOOK_URL")

    parser = argparse.ArgumentParser(
        description="Complete PawConnect Dialogflow CX agent setup",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    parser.add_argument(
        "--project-id",
        default=default_project_id,
        required=not default_project_id,
        help=f"GCP project ID (default: from .env GCP_PROJECT_ID={default_project_id or 'not set'})"
    )
    parser.add_argument(
        "--agent-id",
        default=default_agent_id,
        help=f"Dialogflow CX agent ID (default: from .env DIALOGFLOW_AGENT_ID={default_agent_id or 'auto-detect'})"
    )
    parser.add_argument(
        "--location",
        default=default_location,
        help=f"Agent location (default: from .env DIALOGFLOW_LOCATION={default_location})"
    )
    parser.add_argument(
        "--webhook-url",
        default=default_webhook_url,
        help=f"Webhook URL (default: from .env DIALOGFLOW_WEBHOOK_URL={default_webhook_url or 'not set'})"
    )

    args = parser.parse_args()

    # Configure logging
    logger.remove()
    logger.add(
        sys.stderr,
        format="<level>{message}</level>",
        level="INFO"
    )

    logger.info("╔════════════════════════════════════════╗")
    logger.info("║  PawConnect Dialogflow CX Setup        ║")
    logger.info("╚════════════════════════════════════════╝")
    logger.info("")

    # Find agent if not provided
    agent_id = args.agent_id
    if not agent_id:
        logger.info("Agent ID not provided, auto-detecting...")
        agent_id = find_agent(args.project_id, args.location)
        if not agent_id:
            logger.error("Could not find agent. Please provide --agent-id")
            sys.exit(1)
        logger.info("")

    # Run setup
    setup = DialogflowSetup(
        project_id=args.project_id,
        agent_id=agent_id,
        location=args.location,
        webhook_url=args.webhook_url
    )

    success = setup.run_complete_setup()

    if success:
        logger.info("╔════════════════════════════════════════╗")
        logger.info("║  ✓ Setup Complete!                     ║")
        logger.info("╚════════════════════════════════════════╝")
        logger.info("")
        logger.info("✅ What was configured:")
        logger.info("  • Entity types (housing, experience_level, species, dog_breed, cat_breed, size, age)")
        logger.info("  • Intents with parameter annotations (species + breed + experience)")
        logger.info("  • Pages (Pet Search, Get Recommendations)")
        logger.info("  • Transition routes at flow level")
        logger.info("  • Webhook configuration")
        logger.info("")
        logger.info("📝 Manual step (optional):")
        logger.info("  To add a welcome message, go to Dialogflow Console:")
        logger.info("  Build > Default Start Flow > Entry fulfillment")
        logger.info("  Add: 'Welcome to PawConnect! I'm here to help you")
        logger.info("        find your perfect pet companion.'")
        logger.info("")
        logger.info("🧪 Test in Dialogflow CX Simulator:")
        logger.info("  1. 'I want to adopt a dog in Seattle'")
        logger.info("  2. 'I want to adopt a golden retriever in Portland' (breed-specific)")
        logger.info("  3. 'Yes please show me recommendations'")
        logger.info("  4. 'apartment' (when asked about housing)")
        logger.info("")
        sys.exit(0)
    else:
        logger.error("╔════════════════════════════════════════╗")
        logger.error("║  ✗ Setup Failed                        ║")
        logger.error("╚════════════════════════════════════════╝")
        sys.exit(1)


if __name__ == "__main__":
    main()
