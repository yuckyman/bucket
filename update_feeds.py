#!/usr/bin/env python3
"""
Update feeds.json with new neuroscience-focused feeds
"""

import json
from datetime import datetime, timezone

# Keep the existing hacker news feed
hacker_news_feed = {
    "id": 1,
    "name": "Hacker News",
    "url": "https://hnrss.org/frontpage",
    "description": "Hacker News front page",
    "is_active": True,
    "tags": ["tech", "news"],
    "last_fetched": "2025-09-07T00:01:57.797271+00:00",
    "created_at": "2025-01-06T00:00:00Z"
}

# New feeds structure
new_feeds_data = {
    "tech": {
        "hacker_news": "https://news.ycombinator.com/rss",
        "reddit_python": "https://www.reddit.com/r/python/top/.rss?limit=5"
    },
    "other": {
        "fmhy": "https://fmhy.net/feed.rss"
    },
    "neuroscience": {
        "research": {
            "behavioral_neuroscience": "http://content.apa.org/journals/bne.rss",
            "dreaming": "http://content.apa.org/journals/drm.rss",
            "neuropsychology": "http://content.apa.org/journals/neu.rss",
            "clinical_neuroscience": "http://content.apa.org/journals/cns.rss",
            "psychomusicology": "http://content.apa.org/journals/pmu.rss"
        },
        "pubmed_searches": {
            "brain_computer_interface": "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/erss.cgi?rss_guid=1rSUu--tbw4049Wgf_RdKXdtNCvGW0lVBZFpHe7zaN4k4DwoD5",
            "fnirs": "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/erss.cgi?rss_guid=1JKSd2KF3MGnV7oFVD2g6PNu7rHRFDsLyCNjKkkf4KHBUA3c8P",
            "tdcs_tacs_trns": "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/erss.cgi?rss_guid=143rKCPgMwbasrj66gQ1r1ebioUg42SIGRyVKSoW4m6X-ecQ00",
            "braille": "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/erss.cgi?rss_guid=165yO28ehHLjXJb8W3JvTx2bYozdDe8IvyFRBlOfHZxFR8o1uX",
            "tactile_acuity": "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/erss.cgi?rss_guid=1no_pWrlHWS46ep2l9cVOQkZ1QsEMPlx7YY7aF6AfCIqP-RYZd",
            "low_vision": "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/erss.cgi?rss_guid=1xePBFBNvSIegfqCbvp45N3V9WgCNCS63Z1PLmhwJSPGd18QMT",
            "oostenveld_robert": "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/erss.cgi?rss_guid=1BUB2BG5RbxOblm-hBbiJWEhGG43qlVrvGNHOTqBKva9wWrItM"
        },
        "journals": {
            "journal_neural_engineering": "http://iopscience.iop.org/journal/rss/1741-2552",
            "frontiers_neuroscience": "https://www.frontiersin.org/journals/neuroscience/rss",
            "frontiers_neurorobotics": "https://www.frontiersin.org/journals/neurorobotics/rss",
            "frontiers_human_neuroscience": "https://www.frontiersin.org/journals/human-neuroscience/rss",
            "frontiers_computational_neuroscience": "https://www.frontiersin.org/journals/computational-neuroscience/rss",
            "frontiers_neuroinformatics": "https://www.frontiersin.org/journals/neuroinformatics/rss",
            "pnas_neuroscience": "http://feeds.feedburner.com/ProceedingsOfTheNationalAcademyOfSciencesNeuroscience",
            "journal_neuroscience_current": "http://www.jneurosci.org/rss/current.xml",
            "journal_neuroscience_this_week": "http://www.jneurosci.org/rss/This_Week_in_The_Journal.xml",
            "nature_neuroscience": "http://feeds.nature.com/neuro/rss/current",
            "nature_neuroscience_subjects": "https://www.nature.com/subjects/neuroscience.rss",
            "biorxiv_neuroscience": "http://connect.biorxiv.org/biorxiv_xml.php?subject=neuroscience",
            "neuroimage": "https://rss.sciencedirect.com/publication/science/10538119",
            "journal_neuroscience_methods": "https://rss.sciencedirect.com/publication/science/01650270_OA/open-access",
            "neuroscience_journal": "https://rss.sciencedirect.com/publication/science/03064522",
            "brain_research": "http://rss.sciencedirect.com/publication/science/00068993",
            "clinical_neurophysiology": "https://www.journals.elsevier.com/clinical-neurophysiology/rss",
            "nejm_neurology": "https://search.nejm.org/search?cnt=20&start_month=12&start_year=2008&w=*&restrict=doctype%3Aarticle&srt=0&isort=date&ts=rss&af=topic:1"
        },
        "preprints": {
            "arxiv_qbio_nc": "http://export.arxiv.org/rss/q-bio.NC",
            "arxiv_cs_hc": "http://export.arxiv.org/rss/cs.HC"
        },
        "ieee": {
            "embs": "https://www.embs.org/feed/",
            "cognitive_neuroscience": "https://ieeexplore.ieee.org/rss/TOC6720218.XML",
            "reviews_biomedical_engineering": "https://ieeexplore.ieee.org/rss/TOC4664312.XML",
            "transactions_biomedical_engineering": "https://ieeexplore.ieee.org/rss/TOC10.XML",
            "biosurface_biotribology": "https://ieeexplore.ieee.org/rss/TOC8335903.XML",
            "transactions_haptics": "https://ieeexplore.ieee.org/rss/TOC4543165.XML",
            "brain": "https://brain.ieee.org/feed/",
            "life_sciences": "https://lifesciences.ieee.org/feed/"
        },
        "blogs": {
            "erp_boot_camp": "https://erpinfo.org/blog?format=RSS",
            "sapien_labs": "https://sapienlabs.co/feed/",
            "twenty_percent_statistician": "http://daniellakens.blogspot.com/feeds/posts/default?alt=rss",
            "fens_awards": "https://www.fens.org/RSS/Awards/",
            "fens_news": "https://www.fens.org/RSS/News/"
        }
    }
}

def flatten_feeds(data, parent_path="", feed_id=2):
    """Flatten nested feed structure into flat list"""
    feeds = []
    
    for key, value in data.items():
        current_path = f"{parent_path}_{key}" if parent_path else key
        
        if isinstance(value, dict):
            # Check if this is a feed URL (string) or more nested data
            if all(isinstance(v, str) for v in value.values()):
                # This is a category with feed URLs
                for feed_name, feed_url in value.items():
                    feed_name_clean = feed_name.replace('_', ' ').title()
                    description = f"{current_path.replace('_', ' ').title()} - {feed_name_clean}"
                    
                    # Determine tags based on category
                    tags = []
                    if 'neuroscience' in current_path.lower():
                        tags.extend(['neuroscience', 'research'])
                    if 'tech' in current_path.lower():
                        tags.extend(['tech', 'programming'])
                    if 'pubmed' in current_path.lower():
                        tags.extend(['pubmed', 'research'])
                    if 'journal' in current_path.lower():
                        tags.extend(['journal', 'academic'])
                    if 'ieee' in current_path.lower():
                        tags.extend(['ieee', 'engineering'])
                    if 'arxiv' in current_path.lower():
                        tags.extend(['preprint', 'research'])
                    if 'blog' in current_path.lower():
                        tags.extend(['blog', 'news'])
                    if 'reddit' in feed_name.lower():
                        tags.extend(['reddit', 'community'])
                    if 'fmhy' in feed_name.lower():
                        tags.extend(['tools', 'resources'])
                    
                    feeds.append({
                        "id": feed_id,
                        "name": feed_name_clean,
                        "url": feed_url,
                        "description": description,
                        "is_active": True,
                        "tags": tags,
                        "last_fetched": None,
                        "created_at": datetime.now(timezone.utc).isoformat()
                    })
                    feed_id += 1
            else:
                # More nested data, recurse
                sub_feeds, feed_id = flatten_feeds(value, current_path, feed_id)
                feeds.extend(sub_feeds)
        elif isinstance(value, str):
            # Direct feed URL
            feed_name_clean = key.replace('_', ' ').title()
            description = f"{current_path.replace('_', ' ').title()} - {feed_name_clean}"
            
            tags = []
            if 'neuroscience' in current_path.lower():
                tags.extend(['neuroscience', 'research'])
            if 'tech' in current_path.lower():
                tags.extend(['tech', 'programming'])
            
            feeds.append({
                "id": feed_id,
                "name": feed_name_clean,
                "url": value,
                "description": description,
                "is_active": True,
                "tags": tags,
                "last_fetched": None,
                "created_at": datetime.now(timezone.utc).isoformat()
            })
            feed_id += 1
    
    return feeds, feed_id

def main():
    # Start with hacker news
    all_feeds = [hacker_news_feed]
    
    # Flatten the new feeds structure
    new_feeds, _ = flatten_feeds(new_feeds_data, feed_id=2)
    all_feeds.extend(new_feeds)
    
    # Save to file
    with open('data/feeds.json', 'w') as f:
        json.dump(all_feeds, f, indent=2)
    
    print(f"✅ Updated feeds.json with {len(all_feeds)} feeds")
    print(f"📊 Categories:")
    
    # Count by category
    categories = {}
    for feed in all_feeds:
        for tag in feed['tags']:
            categories[tag] = categories.get(tag, 0) + 1
    
    for category, count in sorted(categories.items()):
        print(f"  {category}: {count} feeds")
    
    print(f"\n🔬 Neuroscience focus: {categories.get('neuroscience', 0)} feeds")
    print(f"🔬 Research focus: {categories.get('research', 0)} feeds")

if __name__ == "__main__":
    main()
