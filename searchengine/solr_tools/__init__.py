import pysolr
import time
import searchengine.debugtools
import urllib

SOLR_URL = "http://localhost:8983/solr/search_engine" #< URL pointing to solr endpoint (including core)
NO_SUBDOMAIN_DOMAIN_BOOST        = '5000'
NO_SUBDOMAIN_META_KEYWORDS_BOOST = '800'
NO_SUBDOMAIN_TITLE_BOOST         = '350'
SUBDOMAIN_DOMAIN_BOOST           = '1000'
SUBDOMAIN_SUBDOMAIN_BOOST        = '600'
SUBDOMAIN_META_KEYWORDS_BOOST    = '400'

##
# @fn   get_solr_instance()
#
# @brief    Gets a solr instance.
#
# @author   Edward Callahan
# @date 8/16/2016
#
# @return   The solr instance.
def get_solr_instance():
    global SOLR_URL
    return pysolr.Solr(SOLR_URL)

##
# @fn   get_boost(subdomain)
#
# @brief    Gets boost for page.
#
# @author   Edward Callahan
# @date 8/16/2016
#
# @param    subdomain   The subdomain.
#
# @return   The boost with information.

def get_boost(subdomain):
    global NO_SUBDOMAIN_DOMAIN_BOOST
    global NO_SUBDOMAIN_META_KEYWORDS_BOOST
    global NO_SUBDOMAIN_TITLE_BOOST
    global SUBDOMAIN_DOMAIN_BOOST
    global SUBDOMAIN_SUBDOMAIN_BOOST
    global SUBDOMAIN_META_KEYWORDS_BOOST
    boost = {}
    if subdomain is None or len(subdomain) == 0 or subdomain == "www":
        boost["domain"]        = NO_SUBDOMAIN_DOMAIN_BOOST
        boost["meta_keywords"] = NO_SUBDOMAIN_META_KEYWORDS_BOOST
        boost["title"]         = NO_SUBDOMAIN_TITLE_BOOST
    else:
        boost["domain"]        = SUBDOMAIN_DOMAIN_BOOST
        boost["meta_keywords"] = SUBDOMAIN_META_KEYWORDS_BOOST
        boost["subdomain"]     = SUBDOMAIN_SUBDOMAIN_BOOST
    return boost

##
# @fn   run_optimizer()
#
# @brief    Executes the optimizer operation.
#
# @author   Edward Callahan
# @date 8/15/2016
def run_optimizer():
    solr = None
    while(True):
        try:
            if solr is None:
                solr = get_solr_instance() 
            searchengine.debugtools.log("Optimizing...")
            solr.commit()
            solr.optimize()
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
    solr = None
    i = 0
    while(True):
        if solr is None:
            solr = get_solr_instance()
        result = solr.search(q='*:*', fq=["-path:['' TO *] AND content:['' TO *] AND title:['' TO *]"], rows = 100, start = (i * 100), timeout=999)
        try:
            for doc in result.docs:
                searchengine.debugtools.log("Reboosting {}...".format(doc["id"]))
                boost = get_boost(doc["subdomain"] if "subdomain" in doc else None)
                doc.pop('_version_', None) # Removing version history if it is in there
                solr.add([doc], boost=boost, commit=False, overwrite=True)
            if len(result.docs) != 100:
                break
            i += 1
        except:
            solr = None
    solr.commit()
            