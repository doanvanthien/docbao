from lib.utils import *
import yaml                   # text-based object serialization
import re                     # regular expression to extract data from article
import pickle                 # python object serialization to save database
import jsonpickle             # json serialization
import math
import operator
import time
from datetime import datetime
from collections import deque # a queue that keep n-last-added item, use for keyword frequent data
import sys


# GLOBAL VARIABLES

count_duyet = 0
count_bo = 0
count_lay = 0
 

# class represents a single article
class Article:
    def __init__(self,article_id,href, topic, date, newspaper, language, summary = ""):
        self._id = article_id
        self._href=href
        self._topic=topic
        self._date=date # date is string ìn format %d/%m%/%Y
        self._summary=summary
        self._newspaper=newspaper
        self._creation_date = datetime.now()
        self._keywords = []
        self._tokenized = False
        self._language = language

    def get_id(self):
        return self._id

    def get_href(self):
        return self._href

    def get_date(self):
        return self._date

    def get_topic(self):
        return self._topic

    def get_newspaper(self):
        return self._newspaper

    def get_summary(self):
        return self._summary

    def get_creation_date(self):
        return self._creation_date

    def get_keywords(self):
        return self._keywords

    def get_language(self):
        return self._language

    def get_date_string(self):
        return self._date.strftime("%d-%m-%y %H:%M")

    def is_tokenized(self):
        return self._tokenized

    def tokenize(self, keyword_manager):
        self._keywords = keyword_manager.get_topic_keyword_list(self.get_topic(), self.get_language())
        self._tokenized = True

# class represents article database
class ArticleManager:
    _data = dict()  # a dict of (href: article)
    _blacklist = dict()  # a dict if {href: lifecount}
    def __init__(self, config_manager, data_filename, blacklist_filename):
        self._config_manager = config_manager
        self._default_blacklist_count = 10 # will be removed after 10 compression
        self._data_filename = data_filename
        self._blacklist_filename = blacklist_filename
        self._id_iterator = 0
    def get_and_increase_id_iterator(self):
        self._id_iterator+=1
        if self._id_iterator==sys.maxsize:
            self._id_iterator = 1
        return self._id_iterator
    def load_data(self):
        stream = open_binary_file_to_read(self._data_filename)
        if stream is not None:
            self._data = pickle.load(stream)
        else:
            print("khong mo duoc file " + self._data_filename)
            self._data = {}

        stream = open_binary_file_to_read(self._blacklist_filename)
        if stream is not None:
            self._blacklist = pickle.load(stream)
        else:
            print("khong mo duoc file " + self._blacklist_filename)
            self._blacklist = {}
        stream = open_binary_file_to_read(self._data_filename + ".log")
        if stream is not None:
            self._id_iterator = pickle.load(stream)
        else:
            print("khong mo duoc file " + self._data_filename + ".log")
            self._id_iterator = 0 

        
    def save_data(self):
        stream = open_binary_file_to_write(self._data_filename)
        pickle.dump(self._data, stream)
        stream.close()

        stream = open_binary_file_to_write(self._blacklist_filename)
        pickle.dump(self._blacklist, stream)
        stream.close()
        
        stream = open_binary_file_to_write(self._data_filename+".log")
        pickle.dump(self._id_iterator, stream)
        stream.close()


    def get_sorted_article_list(self):
        article_list = list(self._data.values())
        article_list.sort(key=lambda x: x.get_creation_date(), reverse=True)
        return article_list

    def get_article(self, href):
        return self._data[href]

    def get_article_by_id(self, id):
        for key in self._data:
            if self._data[key]._id == id:
                return self._data[key]
        return None
    def get_topic_of_an_url(self, url, webconfig, soup=None):
        '''
        function
        --------
        try to find topic on the page url args point to

        algorithm
        -------
        try to find tag / class that are defined in config.txt

        output
        -------
        topic in string
        '''
        use_browser = webconfig.get_use_browser()
        timeout = webconfig.get_browser_timeout()
        if soup is None:
            try:
                soup = read_url_source_as_soup(url, use_browser, timeout)
                if soup is None:
                    return None
            except:
                return None

        if webconfig.get_output_html(): 
            print(soup) #for test

        topic_tag = webconfig.get_topic_tag_list()
        topic_class = webconfig.get_topic_class_list()
        topic_id = webconfig.get_topic_id_list()
       
        topic = None 
        filter = re.compile(webconfig.get_topic_re())
        if topic_tag is not None:
            for tag in topic_tag:
                for foundtag in soup.find_all(tag):
                    tagstring = str(foundtag)
                    searchobj = filter.search(tagstring)  #Search all html tag
                    if searchobj is not None:
                        topic = searchobj.group(1) #Get content of tag

        elif topic_class is not None:
            for _class in topic_class:
                for foundtag in soup.find_all(class_=_class):
                    tagstring = str(foundtag)
                    searchobj = filter.search(tagstring)
                    if searchobj is not None:
                        topic = searchobj.group(1) #Get content of tag


        elif topic_id is not None:
            for topic_id in topic_id:
                for foundtag in soup.find_all(id_=topic_id):
                    tagstring = str(foundtag)
                    searchobj = filter.search(tagstring)
                    if searchobj is not None:
                        topic = searchobj.group(1) #Get content of tag

        if topic is not None:
            return (topic.strip(), soup)
        else:
            return None

    def get_time_of_an_url(self, url, webconfig, soup=None):
        '''
        function
        --------
        try to find published date on the page url args point to

        algorithm
        -------
        try to find tag / class that are defined in config.txt

        '''
        use_browser = webconfig.get_use_browser()
        if soup is None:
            try:
                soup = read_url_source_as_soup(url, use_browser)
                if soup is None:
                    return None
            except:
                return None

        if webconfig.get_output_html():
            print(soup) # for testing
 

        datere = webconfig.get_date_re()
        datetag = webconfig.get_date_tag_list()
        dateclass = webconfig.get_date_class_list()
        date_pattern = webconfig.get_date_pattern()
        filter = re.compile(datere)

        if datetag is not None:
            for tag in datetag:
                for foundtag in soup.find_all(tag):
                    tagstring = str(foundtag) # Get all html of tag
                    # for tagstring in foundtag.contents:
                    searchobj = filter.search(str(tagstring))
                    if searchobj:
                        try: #sometime datetime is not in right pattern
                            return datetime.strptime(searchobj.group(1), date_pattern)
                        except:
                            print("Warning: published date %s is not in %s pattern" % (searchobj.group(1), date_pattern))
                            return datetime.now()
        else:
            for date in dateclass:
                for foundtag in soup.find_all(class_=date):
                    tagstring = str(foundtag) # Get all html of tag
                    #for tagstring in foundtag.contents:
                    searchobj = filter.search(str(tagstring))
                    if searchobj:
                        try: #sometime datetime is not in right pattern
                            return datetime.strptime(searchobj.group(1), date_pattern)
                        except: 
                            print("Warning: published date %s is not in %s pattern" % (searchobj.group(1), date_pattern))
                            return datetime.now()
        return None

    def investigate_if_link_is_valid_article(self, atag, webconfig):
        '''
        function
        --------
        check if atag link point to an article

        algorithm
        --------
        an article will be valid if:
        - href dont' contain any webname in blacklist
        - have published date
        
        return:
        (topic, publish_date) or None if link is not an article
        '''
       
        global count_bo
        soup = None # to reuse soup between crawl topic and crawl publish date function

        fullurl = get_fullurl(webconfig.get_weburl(), atag['href'])
        use_browser= webconfig.get_use_browser()
        topic = ""
        topic_word_list = []
        
        if(webconfig.get_topic_from_link()):
            topic = str(atag.string).strip() # str() is very important !. atag.string is not string and can cause error in jsonpickle
            print("Topic found: %s" % topic)
            topic_word_list = topic.split()
        else:
            #try to crawl topic
            result = self.get_topic_of_an_url(fullurl, webconfig)            
            if result is not None:
                (topic, soup) = result
                print("Topic found: %s" % topic)
                topic_word_list = topic.split()
            else:
                print("Ignore. Can't find topic. This link is not an article")
                return None
        skip_checking_length = webconfig.get_skip_checking_topic_length()
        if (skip_checking_length or len(topic_word_list) >= self._config_manager.get_minimum_word()): # if title length is too short, it might not be an article

            if(webconfig.get_skip_crawl_publish_date()):
                newsdate = datetime.now()
                print("Published at: " + newsdate.strftime("%d-%m-%y %H:%M"))
            else:
                # try to find published date
                newsdate = self.get_time_of_an_url(fullurl, webconfig, soup=soup) 

            if (newsdate is not None): # found an article
                if self.is_not_outdated(newsdate) or webconfig.get_skip_crawl_publish_date():
                    return (topic, newsdate) 
                else:
                    print("Ignore. This article is outdated")
                    count_bo+=1
                    return None
            else:
                print("Ignore. This href don't have published date. It is not an article.")
                count_bo += 1
                return None 
        else:
            print("Ignore. Title is too short. It can't be an article")
            count_bo += 1
            return None 

    def is_in_database(self, href):
        return href in self._data

    def is_blacklisted(self, href):
        return href in self._blacklist

    def add_url_to_blacklist(self, href):
        self._blacklist[href] = self._default_blacklist_count

    def remove_url_from_blacklist(self, href):
        self._blacklist.pop(href)

    def compress_blacklist(self):
        remove =[]
        for href in self._blacklist:
            self._blacklist[href]-=1
            if self._blacklist[href] == 0:
                remove.append(href)
        for href in remove:
            self.remove_url_from_blacklist(href)

    def refresh_url_in_blacklist(self, href): #reward to href when it proves value
        self._blacklist[href]+=1

    def add_article(self, new_article):
        self._data[new_article.get_href()]= new_article

    def add_articles_from_newspaper(self, webconfig): #Get article list from newspaper with webconfig parsing
        global count_lay, count_duyet
        
        webname = webconfig.get_webname()
        weburl = webconfig.get_weburl()
        crawl_url = webconfig.get_crawl_url()
        web_language = webconfig.get_language()
        get_topic = webconfig.get_topic_from_link()
        use_browser = webconfig.get_use_browser()
        count_visit = 0 # to limit number of url to visit in each turn
        maximum_url_to_visit = self._config_manager.get_maximum_url_to_visit_each_turn()
        print()
        print("Crawling newspaper: " + webname)
        a=True
        while a==True:
        #try:
            soup = read_url_source_as_soup(crawl_url, use_browser)
            if soup is not None:
                if get_topic: #from link
                    ataglist = soup.find_all("a", text=True, href=True)
                else:
                    ataglist = soup.find_all("a", href=True)
                   
                print("Getting data, please wait...")
                for atag in ataglist:
                    # loc ket qua
                    fullurl = get_fullurl(weburl, atag['href'])
                    print()
                    print("Processing page: " + fullurl)
                    count_duyet += 1

                    if not self.is_blacklisted(fullurl):
                        if not self.is_in_database(fullurl):
                            # check if fullurl satisfies url pattern
                            filter = re.compile(webconfig.get_url_pattern_re(), re.IGNORECASE)
                            if filter.match(fullurl) is None:
                                print("Ignore. This url is from another site")
                            else:
    
                                count_visit +=1
                                result = self.investigate_if_link_is_valid_article(atag, webconfig)
                                if result is not None: # is valid article 
    
                                    (topic, publish_date) = result

                                    next_id = self.get_and_increase_id_iterator()
                                    
                                    self.add_article(Article(article_id=next_id,topic=topic, 
                                                     date = publish_date,
                                                     newspaper = webname, href=fullurl, language=web_language))
                                    count_lay +=1
                                    print("Crawled articles: " + str(count_lay))

                                    # wait for n second before continue crawl
                                    waiting_time = self._config_manager.get_waiting_time_between_each_crawl()
                                    print("Waiting %s seconds before continue crawling" % str(waiting_time))
                                    time.sleep(waiting_time + random.random()*3)
 
                                else:
                                    self.add_url_to_blacklist(fullurl)
                                    print("Add to blacklist")
                                if count_visit >= maximum_url_to_visit:  # Stop crawling to not get caught by server
                                    print("Stop crawling %s to avoid being caught by server" % webname)
                                    return None
                        else:
                            print("This article has been in database")
                    else:
                        print("This link is in blacklist database")
                        self.refresh_url_in_blacklist(fullurl)
            else:
                print("Can't open: " + webname)
            a=False
        #except:
        #    print("Can't open: " + webname)

    def is_not_outdated(self, date):
        return (datetime.now() - date).days <= self._config_manager.get_maximum_day_difference()

    def is_article_topic_too_short(self, article):
        return len(article.get_topic().split()) < self._config_manager.get_minimum_word()

    def remove_article(self, article):
        self._data.pop(article.get_href())

    def count_database(self):
        return len(self._data)

    def count_blacklist(self):
        return len(self._blacklist)

    def count_tokenized_articles_contain_keyword(self, keyword):
        count = 0
        for href in self._data:
            article = self._data[href]
            if (article.is_tokenized is True) and (keyword in article.get_topic().lower()):
                count+=1
        return count

    def compress_database(self, _keyword_manager):
        remove = []
        for url, article in self._data.items():
            if not self.is_not_outdated(article.get_date()) or self.is_article_topic_too_short(article):
                remove.append(article)
                self.add_url_to_blacklist(url)
        for article in remove:
            _keyword_manager.build_keyword_list_after_remove_article(article)
            self.remove_article(article)

    def reset_tokenize_status(self):
        for href, article in self._data.items():
            article._tokenized = False

