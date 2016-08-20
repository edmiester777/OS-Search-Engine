import pysolr
import time
import searchengine.debugtools
import urllib
import math

SOLR_URLS = {
    'main' : [
        'http://localhost:8983/solr/search_engine/',
        'http://localhost:7574/solr/search_engine/'
    ],
    'working' : [
        'http://localhost:8983/solr/search_engine_working/',
        'http://localhost:7574/solr/search_engine_working/'
    ]
} #< Dictionary of urls used for each endpoint for our solr server nodes.

NO_SUBDOMAIN_DOMAIN_BOOST        = '5000'
NO_SUBDOMAIN_META_KEYWORDS_BOOST = '800'
NO_SUBDOMAIN_TITLE_BOOST         = '350'
SUBDOMAIN_DOMAIN_BOOST           = '1000'
SUBDOMAIN_SUBDOMAIN_BOOST        = '600'
SUBDOMAIN_META_KEYWORDS_BOOST    = '400'

##
# @fn   get_solr_instance(collection = 'main', url_offset = 0)
#
# @brief    Gets a solr instance.
#
# @author   Edward Callahan
# @date 8/16/2016
#
# @param    optional collection collection     core        The optional core.
#                                                          'main' = main solr core 'working' =
#                                                          working solr core.
# @param    optional url_offset port_offset    url_offset  Offset for ports (used to balance
#                               workload in solrcloud)
#
# @return   The solr instance.

def get_solr_instance(collection = 'main', url_offset = 0):
    global SOLR_URLS
    return pysolr.Solr(SOLR_URLS[collection][url_offset % len(SOLR_URLS[collection])])

##
# @fn   get_boost(doc)
#
# @brief    Gets boost for page.
#
# @author   Edward Callahan
# @date 8/16/2016
#
# @param    document to determine the boost for.
#
# @return   The boost with information.
def get_boost(doc):
    global NO_SUBDOMAIN_DOMAIN_BOOST
    global NO_SUBDOMAIN_META_KEYWORDS_BOOST
    global NO_SUBDOMAIN_TITLE_BOOST
    global SUBDOMAIN_DOMAIN_BOOST
    global SUBDOMAIN_SUBDOMAIN_BOOST
    global SUBDOMAIN_META_KEYWORDS_BOOST

    # checking to ensure this doc is worth boost
    if 'path' in doc and len(doc['path']) > 0:
        return None

    boost = {}
    if "subdomain" not in doc or len(doc["subdomain"]) == 0 or doc["subdomain"] == "www":
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
            solr = get_solr_instance('main')
        result = solr.search(q='domain:* AND -path:*', rows = 100, start = (i * 100), timeout=999)
        try:
            if len(result.docs) == 0 or result.docs is None:
                break
            for doc in result.docs:
                searchengine.debugtools.log("Reboosting {}...".format(doc["id"]))
                boost = get_boost(doc)
                doc.pop('_version_', None) # Removing version history if it is in there
                solr.add([doc], boost=boost, commit=False, overwrite=True)
            i += 1
        except Exception as ex:
            searchengine.debugtools.log_exception(ex)
            solr = None
    solr.commit()

##
# @fn   run_delta_merge(rows_per_iteration = 500)
#
# @brief    Migrate new data from working core to live core.
#
# @author   Edward Callahan
# @date 8/17/2016
#
# @param    optional rows_per_iteration Rows to migrate per iteration.

def run_delta_merge(rows_per_iteration = 500):
    solr_working = None
    solr_main = None
    i = 0
    num_iterations = -1
    has_printed = False
    start_time = str(int(time.time()))
    while(num_iterations < 0 or i < num_iterations):
        if solr_working is None:
            solr_working = get_solr_instance('working')
        if solr_main is None:
            solr_main = get_solr_instance('main')
        result = solr_working.search(q= '*:*', fq="last_update_time:[0 TO " + start_time + "] AND domain:*", rows = rows_per_iteration)
        docs_to_add_working = []
        docs_to_add_main = []
        if not has_printed:
            num_found = result.raw_response["response"]["numFound"]
            num_iterations = math.ceil(num_found / rows_per_iteration)
            searchengine.debugtools.log("Total: {:,}, {:,} iterations".format(num_found, num_iterations))
            has_printed = True
        try:
            if len(result.docs) == 0 or result.docs is None:
                break
            for doc in result.docs:
                docs_to_add_working.append({
                    "id"               : doc["id"],
                    "is_https"         : doc["is_https"],
                    "last_update_time" : int(time.time())
                })
                if 'domain' in doc and 'content' in doc:
                    doc.pop('_version_', None) # Removing version history if it is in there
                    doc.pop('last_update_time', None) # Removing last_update_time (not needed in main core)
                    docs_to_add_main.append(doc)
            searchengine.debugtools.log("Migrating {:,} documents... ({}/{})".format(len(docs_to_add_main), i + 1, num_iterations))
            solr_main.add(docs_to_add_main, overwrite=True)
            solr_working.add(docs_to_add_working, overwrite=True)
            i += 1
        except Exception as ex:
            searchengine.debugtools.log("EXCEPTION:")
            searchengine.debugtools.log_exception(ex)
            solr_working = None
            solr_main = None
    searchengine.debugtools.log("Running rebooster...")
    run_rebooster()  
    searchengine.debugtools.log("Done.")  