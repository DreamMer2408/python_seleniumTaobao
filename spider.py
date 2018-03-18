from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.proxy import Proxy
import re
from pyquery import PyQuery as pq
import pymongo
import time
import requests
import os


#链接数据库
client=pymongo.MongoClient('localhost',27017)
taobao=client['taobao']
product=taobao['product']
#获取代理
PROXY_POOL_URL='http://127.0.0.1:5000/get'
#使用Chrome浏览器构造webdriver对象
browser=webdriver.Chrome()
#等待加载，最多十秒
wait=WebDriverWait(browser,10)

heads={
'Host':'weixin.sogou.com',
'Referer':'http://weixin.sogou.com/weixin?query=%E9%A3%8E%E6%99%AF&_sug_type_=&sut=61884&lkt=1%2C1520008874181%2C1520008874181&s_from=input&_sug_=y&type=2&sst0=1520008874284&page=47&ie=utf8&w=01019900&dr=1',
'Upgrade-Insecure-Requests':'1',
'User-Agent':'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/55.0.2883.87 UBrowser/6.2.3964.2 Safari/537.36'
}

def search():
    print('正在搜索...')
    try:
        browser.get('http://www.taobao.com')
        #获取搜索框
        input=wait.until(EC.presence_of_element_located((By.CSS_SELECTOR,'#q')))
        #获取提交按钮
        submit=wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR,'#J_TSearchForm > div.search-button > button')))
        #模拟键盘输入关键字
        input.send_keys('美食')
        #模拟鼠标点击
        submit.click()
        #获取底部翻页
        pages=wait.until(EC.presence_of_element_located((By.CSS_SELECTOR,'#mainsrp-pager > div > div > div > div.total')))
        get_products()
        return pages.text
    except TimeoutException:
        print('请求超时,网不好吧')
        return search()

def next_page(page_number):
    print('在第{}页'.format(page_number))
    try:
        input = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, '#mainsrp-pager > div > div > div > div.form > input')))
        submit = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, '#mainsrp-pager > div > div > div > div.form > span.btn.J_Submit')))
        #清除输入内容
        input.clear()
        #输入页码
        input.send_keys(page_number)
        #鼠标点击
        submit.click()
        wait.until(EC.text_to_be_present_in_element((By.CSS_SELECTOR,'#mainsrp-pager > div > div > div > ul > li.item.active > span'),str(page_number)))
        get_products()
    except TimeoutException:
        return next_page(page_number)

def get_products():
    #检测商品是否存在
    wait.until(EC.presence_of_element_located((By.CSS_SELECTOR,'#mainsrp-itemlist .items .item')))
    html=browser.page_source
    doc=pq(html)
    items=doc('#mainsrp-itemlist .items .item').items()
    for item in items:
        product={
            'title':item.find('.title').text(),
            'image':item.find('.pic .img').attr('src'),
            'price':item.find('.price').text()[1:],
            'deal':item.find('.deal-cnt').text(),
            'shop':item.find('.shopname').text(),
            #'goods_id':'https://detail.tmall.com/item.htm?id={}'.format(nid),
            'location':item.find('.location').text()
        }
        print(product)
        save_to_Mongo(product)
    time.sleep(2)

def save_to_Mongo(result):
    try:
        if product.insert_one(result):
            print('存储到数据库成功',result)
    except Exception:
        print('存储到数据库失败',result)

#添加代理
def get_proxy():
    try:
        response=requests.get(PROXY_POOL_URL)
        if response.status_code==200:
            return response.text
        return None
    except ConnectionError:
        return None

if __name__ == '__main__':
    try:
        pages=int(re.compile('(\d+)').search(search()).group(1))
        #翻页
        for i in range(2,pages):
            next_page(i)
    except Exception:
        print('出错啦',Exception)
    finally:
        browser.close()
