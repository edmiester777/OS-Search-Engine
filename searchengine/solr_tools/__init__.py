import pysolr
import time
import searchengine.debugtools
import urllib

SOLR_URL = "http://localhost:8983/solr/search_engine" #< URL pointing to solr endpoint (including core)
SOLR_INSTANCE = None
NO_SUBDOMAIN_DOMAIN_BOOST        = '5000'
NO_SUBDOMAIN_META_KEYWORDS_BOOST = '800'
NO_SUBDOMAIN_TITLE_BOOST         = '350'
SUBDOMAIN_DOMAIN_BOOST           = '1000'
SUBDOMAIN_SUBDOMAIN_BOOST        = '600'
SUBDOMAIN_META_KEYWORDS_BOOST    = '400'

##
# @fn   run_optimizer()
#
# @brief    Executes the optimizer operation.
#
# @author   Edward Callahan
# @date 8/15/2016
def run_optimizer():
    global SOLR_URL
    global SOLR_INSTANCE  
    while(True):
        try:
            if SOLR_INSTANCE is None:
                SOLR_INSTANCE = pysolr.Solr(SOLR_URL)  
            searchengine.debugtools.log("Optimizing...")
            SOLR_INSTANCE.commit()
            SOLR_INSTANCE.optimize()
            searchengine.debugtools.log("Done.")
            time.sleep(60 * 5)
        except:
            searchengine.debugtools.log("Disconnected.")
            SOLR_INSTANCE = None
            time.sleep(60 * 10) # Sleeping because we crashed due to timeout.

##
# @fn   run_rebooster()
#
# @brief    Run the rebooster (used for rewriting index-time boost values).
#
# @author   Edward Callahan
# @date 8/15/2016
def run_rebooster():
    global SOLR_URL
    global SOLR_INSTANCE
    global NO_SUBDOMAIN_DOMAIN_BOOST
    global NO_SUBDOMAIN_META_KEYWORDS_BOOST
    global NO_SUBDOMAIN_TITLE_BOOST
    global SUBDOMAIN_DOMAIN_BOOST
    global SUBDOMAIN_SUBDOMAIN_BOOST
    global SUBDOMAIN_META_KEYWORDS_BOOST
    if SOLR_INSTANCE is None:
        SOLR_INSTANCE = pysolr.Solr(SOLR_URL)
    i = 0
    while(True):
        result = SOLR_INSTANCE.search(q='*:*', fq=["-path:['' TO *] AND content:['' TO *] AND title:['' TO *]"], rows = 100, start = (i * 100), timeout=999)
        try:
            for doc in result.docs:
                searchengine.debugtools.log("Reboosting {}...".format(doc["id"]))
                doc.pop('_version_', None) # Removing version history if it is in there
                boost = {}
                if not 'subdomain' in doc or len(doc["subdomain"]) == 0:
                    boost["domain"]        = NO_SUBDOMAIN_DOMAIN_BOOST
                    boost["meta_keywords"] = NO_SUBDOMAIN_META_KEYWORDS_BOOST
                    boost["title"]         = NO_SUBDOMAIN_TITLE_BOOST
                else:
                    boost["domain"]        = SUBDOMAIN_DOMAIN_BOOST
                    boost["meta_keywords"] = SUBDOMAIN_META_KEYWORDS_BOOST
                    boost["subdomain"]     = SUBDOMAIN_SUBDOMAIN_BOOST
                SOLR_INSTANCE.add([doc], boost=boost, commit=False, overwrite=True)
            if len(result.docs) != 100:
                break
            i += 1
        except:
            SOLR_INSTANCE = pysolr.Solr(SOLR_URL)
    SOLR_INSTANCE.commit()
            