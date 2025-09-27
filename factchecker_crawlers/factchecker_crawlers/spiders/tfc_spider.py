import scrapy
import re
from ..items import TFCReportItem

class TfcSpiderSpider(scrapy.Spider):
    name = "tfc_spider"
    allowed_domains = ["tfc-taiwan.org.tw"]
    start_urls = ["https://tfc-taiwan.org.tw/fact-check-reports-all/"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.item_count = 0

        start_page = kwargs.get('start_page')
        end_page = kwargs.get('end_page')

        if start_page is None and end_page is None and len(args) > 0:
            if len(args) == 1:
                # 一個參數：end_page
                end_page = args[0]
                start_page = None
            elif len(args) == 2:
                # 兩個參數：start_page, end_page
                start_page = args[0]
                end_page = args[1]

        if start_page is None and end_page is None:
            # 沒有輸入參數：從第1頁爬到最後一頁
            self.start_page = 1
            self.end_page = None  
        elif start_page is None and end_page is not None:
            # 只輸入一個參數：從第1頁開始，爬到指定頁數
            self.start_page = 1
            self.end_page = int(end_page)
        else:
            # 輸入兩個參數
            self.start_page = int(start_page) if start_page is not None else 1
            self.end_page = int(end_page) if end_page is not None else 1

        # 檢查是否有目標URL參數
        if hasattr(self, 'target_url') and self.target_url:
            self.start_urls = [self.target_url]
        else:
            self.start_urls = [f"https://tfc-taiwan.org.tw/fact-check-reports-all/?pg={self.start_page}"]

    def parse(self, response):
        # 如果是特定文章URL，直接解析文章
        if hasattr(self, 'target_url') and self.target_url and response.url == self.target_url:
            yield from self.parse_article(response)
            return
        
        """解析頁面（列表頁面或單篇文章）"""
        self.logger.info(f"解析頁面: {response.url}")
        
        # 提取文章連結
        article_links = response.css('li.kb-query-item a.kb-section-link-overlay::attr(href)').getall()
        
        self.logger.info(f"找到 {len(article_links)} 篇文章")
        
        # 處理每篇文章
        for link in article_links:
            if link and '/fact-check-reports/' in link:
                absolute_url = response.urljoin(link)
                yield scrapy.Request(
                    url=absolute_url,
                    callback=self.parse_article,
                    dont_filter=True
                )
        
        # 處理分頁，只爬取指定範圍內的頁面
        if not hasattr(self, 'target_url') or not self.target_url:
            current_page = self._extract_current_page(response.url)

            if self.end_page is None:
                max_pages = self._extract_max_pages(response)
                self.end_page = max_pages
                self.logger.info(f"設定結束頁面為總頁數: {self.end_page}")

            # 生成下一頁的請求
            if current_page < self.end_page:
                next_page = current_page + 1
                next_url = f"https://tfc-taiwan.org.tw/fact-check-reports-all/?pg={next_page}"
                self.logger.info(f"準備爬取下一頁: {next_page} (範圍: {self.start_page}-{self.end_page})")
                yield scrapy.Request(
                    url=next_url,
                    callback=self.parse,
                    dont_filter=True
                )

    def parse_article(self, response):
        """解析單篇文章詳情"""
        self.logger.info(f"解析文章: {response.url}")
        
        item = TFCReportItem()
        
        # 基本欄位
        item['content_url'] = response.url
        item['source'] = 'TFC'
        
        # 標題
        title = response.css('title::text').get()
        if title:
            title = title.replace(' - 看見真實，才能打造美好台灣', '').strip()
        item['title'] = title.strip() if title else ''
        
        # 保存當前標題供 metadata 解析使用
        self._current_title = item['title']
        
        # 內容
        content_selectors = [
            '.post-content', 
            '.single-content',
        ]
        
        content = ""
        for selector in content_selectors:
            content_elem = response.css(selector)
            if content_elem:
                # 提取所有文字，移除script和style標籤
                content = content_elem.css('*:not(script):not(style)::text').getall()
                content = ' '.join([text.strip() for text in content if text.strip()])
                break
        
        # 從content中解析metadata並提取內容
        parsed_data = self._parse_content_metadata(content)
        # print(content + '\n')
        
        item['content'] = content  # 保留原始內容
        item['processed_content'] = parsed_data['processed_content']  # 純內容
        
        # 查核結果
        item['check_result'] = parsed_data['check_result'] or self._extract_classification(response)
        
        # 發布日期和更新日期  
        item['publish_date'] = parsed_data['publish_date']
        item['update_date'] = parsed_data['update_date']
        
        # 分類標籤
        categories = parsed_data['categories']
        if not categories:
            category_links = response.css('.entry-taxonomies .category-links a::text').getall()
            categories = [cat.strip() for cat in category_links if cat.strip()]
        
        # 如果分類是"未勾選屬性"，設置為空
        if categories and len(categories) == 1 and categories[0] == "未勾選屬性":
            categories = []
        
        item['categories'] = categories
        
        # 報告編號
        item['report_number'] = parsed_data['report_number']
        
        # 記者和編輯信息
        item['reporter'] = parsed_data['reporter']
        item['editor'] = parsed_data['editor']
        
        # 增加計數器
        self.item_count += 1
        self.logger.info(f"已處理 {self.item_count} 篇文章")
        
        yield item
    
    def _extract_current_page(self, url):
        """從URL提取當前頁碼"""
        match = re.search(r'[?&]pg=(\d+)', url)
        return int(match.group(1)) if match else 1
    
    def _extract_max_pages(self, response):
        """提取最大頁數"""
        max_pages = response.css('[data-max-num-pages]::attr(data-max-num-pages)').get()
        if max_pages:
            return int(max_pages)
    
    def _extract_classification(self, response):
        classes = response.css('body ::attr(class)').getall()
        all_classes = ' '.join(classes)
        
        if 'incorrect' in all_classes or 'error' in all_classes:
            return '錯誤'
        elif 'partial' in all_classes:
            return '部分錯誤'  
        elif 'clarification' in all_classes:
            return '事實釐清'
        elif 'correct' in all_classes:
            return '正確'

        return ''
    
    def _parse_content_metadata(self, content):
        """從content中解析metadata並提取純內容"""
        
        result = {
            'check_result': '',
            'publish_date': '',
            'update_date': '',
            'categories': [],
            'report_number': '',
            'reporter': '',
            'editor': '',
            'processed_content': content
        }
        
        if not content:
            return result
        
        # 預處理：找到文章正文起始位置
        result['processed_content'] = self._extract_article_content(content)
        
        # 嘗試不同的 metadata 模式匹配，按優先順序
        patterns = [
            # 模式1: 完整的舊版格式
            {
                'name': 'legacy_complete',
                'pattern': r'(錯誤|部分錯誤|事實釐清|正確)\s+(.*?)\s+發佈：?\s*(\d{4}-\d{2}-\d{2})\s*(?:更新：?\s*(\d{4}-\d{2}-\d{2}))?\s*報告編號\s*：?\s*(\d+)\s*(?:查核)?記者：?\s*([^責]+?)\s*責任編輯：?\s*([^\s內容背景查核]+)',
                'groups': {
                    'check_result': 1, 'categories': 2, 'publish_date': 3, 
                    'update_date': 4, 'report_number': 5, 'reporter': 6, 'editor': 7
                }
            },
            # 模式2: 新版格式（含更新版本）
            {
                'name': 'new_format_with_update',
                'pattern': r'事實查核報告#(\d+)\s+【([^】]+)】.*?發布日期／(\d{4}-\d{2}-\d{2})\s+\d{2}:\d{2}:\d{2}\s+【報告將隨時更新\s+(\d{4}/\d{2}/\d{2})版】',
                'groups': {
                    'report_number': 1, 'check_result': 2, 'publish_date': 3, 'update_date': 4
                }
            },
            # 模式3: 舊版事實查核報告格式
            {
                'name': 'old_fact_check_format',
                'pattern': r'事實查核報告#(\d+)\s+【([^】]+)】[^發]*?發布日期／(\d{4}-\d{2}-\d{2})\s+\d{2}:\d{2}:\d{2}',
                'groups': {
                    'report_number': 1, 'check_result': 2, 'publish_date': 3
                }
            }
        ]
        
        # 嘗試匹配完整格式
        matched = False
        for pattern_info in patterns:
            match = re.search(pattern_info['pattern'], content)
            if match:
                self._extract_from_match(result, match, pattern_info['groups'])
                matched = True
                
                # 特殊處理：更新日期格式轉換
                if pattern_info['name'] == 'new_format_with_update' and result['update_date']:
                    result['update_date'] = result['update_date'].replace('/', '-')
                
                # 如果沒有更新日期，使用發布日期
                if not result['update_date'] and result['publish_date']:
                    result['update_date'] = result['publish_date']
                
                break
        
        # 如果沒有匹配到完整格式，逐個提取字段
        if not matched:
            self._extract_individual_fields(result, content)
        
        # 如果仍然沒有分類結果，從標題中提取（針對 migration 文章）
        if not result['check_result']:
            result['check_result'] = self._extract_from_title()
        
        # 統一處理分類重新歸類
        result['check_result'] = self._normalize_classification(result['check_result'])
        
        # 清理處理後的內容
        result['processed_content'] = self._clean_processed_content(result['processed_content'])
        
        return result
    
    def _extract_article_content(self, content):
        """提取文章正文內容"""
        # 尋找分享按鈕位置作為文章起始點
        share_pattern = r'Share on Facebook Share on Threads Share on Pinterest Share on LINE Email this Page Print this Page\s*'
        share_match = re.search(share_pattern, content)
        
        if share_match:
            return content[share_match.end():].strip()
        return content
    
    def _extract_from_match(self, result, match, groups):
        """從正則匹配結果中提取數據"""
        for field, group_index in groups.items():
            if group_index <= len(match.groups()) and match.group(group_index):
                value = match.group(group_index).strip()
                
                if field == 'categories':
                    result[field] = [value]
                elif field == 'reporter':
                    result[field] = value.rstrip('、')
                else:
                    result[field] = value
    
    def _extract_individual_fields(self, result, content):
        """逐個提取各個字段"""
        # 提取分類
        class_patterns = [
            r'【(錯誤|部分錯誤|事實釐清|正確|易生誤解|證據不足)】',  # 從標題格式
            r'(?:^|\s)(錯誤|部分錯誤|事實釐清|正確|易生誤解|證據不足)(?:\s|$)'  # 從內容前1000字符
        ]
        
        for pattern in class_patterns:
            search_content = content[:1000] if '(?:^|\\s)' in pattern else content
            match = re.search(pattern, search_content)
            if match:
                result['check_result'] = match.group(1)
                break
        
        # 提取日期
        date_patterns = [
            r'發佈：?\s*(\d{4}-\d{2}-\d{2})',
            r'發布日期／(\d{4}-\d{2}-\d{2})'
        ]
        
        for pattern in date_patterns:
            match = re.search(pattern, content)
            if match:
                result['publish_date'] = match.group(1)
                break
        
        # 提取更新日期
        update_match = re.search(r'更新：?\s*(\d{4}-\d{2}-\d{2})', content)
        if update_match:
            result['update_date'] = update_match.group(1)
        elif result['publish_date']:
            result['update_date'] = result['publish_date']
        
        # 提取報告編號
        report_patterns = [
            r'事實查核報告#(\d+)',
            r'報告編號\s*：?\s*(\d+)'
        ]
        
        for pattern in report_patterns:
            match = re.search(pattern, content)
            if match:
                result['report_number'] = match.group(1)
                break
        
        # 提取記者和編輯信息
        # 嘗試括號格式
        reporter_editor_match = re.search(r'（記者：([^；]+)；責任編輯：([^）]+)）', content)
        if reporter_editor_match:
            result['reporter'] = reporter_editor_match.group(1).strip()
            result['editor'] = reporter_editor_match.group(2).strip()
        else:
            # 分別提取
            reporter_match = re.search(r'(?:查核)?記者：?\s*([^責任編輯]+?)(?:\s*責任編輯|$)', content)
            if reporter_match:
                result['reporter'] = reporter_match.group(1).strip().rstrip('、')
            
            editor_match = re.search(r'責任編輯：?\s*([^\s內容背景查核]+)', content)
            if editor_match:
                result['editor'] = editor_match.group(1).strip()
    
    def _extract_from_title(self):
        """從標題中提取分類（針對 migration 文章）"""
        if hasattr(self, '_current_title') and self._current_title:
            title_match = re.search(r'【(錯誤|部分錯誤|事實釐清|正確|易生誤解|證據不足)】', self._current_title)
            if title_match:
                self.logger.info(f"從標題中提取到分類: {title_match.group(1)}")
                return title_match.group(1)
        return ''
    
    def _normalize_classification(self, classification):
        """統一處理分類標準化"""
        if classification == '易生誤解':
            return '錯誤'
        return classification
    
    def _clean_processed_content(self, content):
        """清理處理後的內容，移除 metadata"""
        # 移除各種 metadata 格式
        cleanup_patterns = [
            r'【報告將隨時更新[^】]*】\s*',
            r'^事實查核報告#\d+\s+.*?發布日期／\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}\s*',
            r'^【[^】]+】.*?發布日期／\d{4}-\d{2}-\d{2}.*$',
            r'事實查核報告#\d+\s+【[^】]+】[^【]*【報告將隨時更新[^】]*】\s*',
            r'事實查核報告#\d+\s+【[^】]+】[^一二三四五六七八九十]*?發布日期／\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}\s*'
        ]
        
        for pattern in cleanup_patterns:
            if '^' in pattern:
                content = re.sub(pattern, '', content, flags=re.MULTILINE)
            else:
                content = re.sub(pattern, '', content, flags=re.MULTILINE | re.DOTALL)
        
        return content.strip()