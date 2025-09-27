# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html

import json
import os
from datetime import datetime
from itemadapter import ItemAdapter


class FactcheckerCrawlersPipeline:
    def open_spider(self, spider):
        os.makedirs('output', exist_ok=True)
        
        self.items = []
        self.unsorted_filename = 'output/tfc_reports_unsorted.json'
        
        # 初始化檔案（清空舊內容）
        with open(self.unsorted_filename, 'w', encoding='utf-8') as f:
            f.write('[\n')
        self.first_item = True
        
        spider.logger.info("開始收集資料...")

    def close_spider(self, spider):
        if not self.items:
            spider.logger.info("沒有資料可以輸出")
            return
            
        try:
            # 關閉未排序檔案的 JSON 陣列
            with open(self.unsorted_filename, 'a', encoding='utf-8') as f:
                f.write('\n]')
            
            # 依照 report_number 由新到舊排序（數字越大越新）
            try:
                def get_sort_key(item):
                    report_num = item.get('report_number', '').strip()
                    if report_num and report_num.isdigit():
                        return int(report_num)
                    else:
                        return -1  # 空的 report_number 排在最後
                
                sorted_items = sorted(self.items, key=get_sort_key, reverse=True)
            except (ValueError, TypeError) as e:
                spider.logger.error(f"排序時發生錯誤: {e}，使用原始順序")
                sorted_items = self.items.copy()
            
            # 寫入排序後的資料
            sorted_filename = 'output/tfc_reports_sorted.json'
            with open(sorted_filename, 'w', encoding='utf-8') as f:
                json.dump(sorted_items, f, ensure_ascii=False, indent=4)
            
            spider.logger.info(f"已輸出 {len(self.items)} 筆資料到 {self.unsorted_filename}（未排序，格式化）")
            spider.logger.info(f"已輸出 {len(sorted_items)} 筆資料到 {sorted_filename}（按報告編號由新到舊排序）")
            
        except Exception as e:
            spider.logger.error(f"寫入檔案時發生錯誤: {e}")

    def process_item(self, item, spider):
        adapter = ItemAdapter(item)
        
        # 清理數據
        for field_name, value in adapter.items():
            if isinstance(value, str):
                # 移除多餘的空白字符
                adapter[field_name] = value.strip()
        
        item_dict = dict(adapter)
        
        # 將項目加入列表
        self.items.append(item_dict)
        
        # 一邊抓一邊寫入未排序檔案
        try:
            with open(self.unsorted_filename, 'a', encoding='utf-8') as f:
                if not self.first_item:
                    f.write(',\n')
                else:
                    self.first_item = False
                json.dump(item_dict, f, ensure_ascii=False, indent=4)
            
            spider.logger.info(f"已即時寫入第 {len(self.items)} 筆資料到 {self.unsorted_filename}")
            
        except Exception as e:
            spider.logger.error(f"即時寫入資料時發生錯誤: {e}")
        
        return item
