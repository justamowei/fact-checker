import sys
import subprocess
import os

def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_dir = script_dir 

    # 解析參數
    args = sys.argv[1:]

    if len(args) == 0:
        # 沒有參數：爬取所有頁面
        cmd = ['scrapy', 'crawl', 'tfc_spider']
    elif len(args) == 1:
        arg = args[0]
        if arg in ['--help', '-h', 'help']:
            # 顯示幫助信息
            print("TFC Spider 入口")
            print("  python run_tfc_spider.py                               # 爬取所有頁面")
            print("  python run_tfc_spider.py <pages>                       # 爬取前 N 頁")
            print("  python run_tfc_spider.py <start> <end>                 # 爬取從 start 到 end 頁")
            print("  python run_tfc_spider.py https://tfc-taiwan.org.tw...  # 爬取特定文章")
            print("  python run_tfc_spider.py --help                        # 顯示此幫助信息")
            sys.exit(0)
        elif arg.startswith('http'):
            # URL 參數：爬取特定文章
            cmd = ['scrapy', 'crawl', 'tfc_spider', '-a', f'target_url={arg}']
        else:
            # 一個參數：爬取前 N 頁
            try:
                pages = int(arg)
                cmd = ['scrapy', 'crawl', 'tfc_spider', '-a', f'end_page={pages}']
            except ValueError:
                print(f"錯誤：參數必須是數字或 URL，得到：{arg}")
                sys.exit(1)
    elif len(args) == 2:
        # 兩個參數：start_page 和 end_page
        try:
            start_page = int(args[0])
            end_page = int(args[1])
            cmd = ['scrapy', 'crawl', 'tfc_spider', '-a', f'start_page={start_page}', '-a', f'end_page={end_page}']
        except ValueError:
            print(f"錯誤：參數必須是數字，得到：{args[0]}, {args[1]}")
            sys.exit(1)
    else:
        print("用法：")
        print("  python run_tfc_spider.py                               # 爬取所有頁面")
        print("  python run_tfc_spider.py <pages>                       # 爬取前 N 頁")
        print("  python run_tfc_spider.py <start> <end>                 # 爬取從 start 到 end 頁")
        print("  python run_tfc_spider.py https://tfc-taiwan.org.tw...  # 爬取特定文章")
        print("  python run_tfc_spider.py --help                        # 顯示此幫助信息")
        sys.exit(1)

    # 切換到專案目錄並執行命令
    os.chdir(project_dir)
    print(f"執行命令：{' '.join(cmd)}")
    result = subprocess.run(cmd)

    # 返回 Scrapy 的退出碼
    sys.exit(result.returncode)

if __name__ == '__main__':
    main()