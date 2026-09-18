飛航模飾 Shopline -> LINE 每日業績廣播｜GitHub Actions 部署包
================================================================

這個資料夾裡有兩個檔案，請照原本的資料夾結構放進你的 GitHub repo：

  shopline_daily_summary.py                          -> 放在 repo 根目錄
  .github/workflows/shopline-daily-report.yml         -> 放在 repo 的 .github/workflows/ 底下（路徑不能改）

設定步驟
--------
1. 到 https://github.com/new 建立一個新的 repository（建議設為 Private）。

2. 把上面兩個檔案（含資料夾結構）上傳到這個 repo：
   - 網頁版：點「Add file」→「Upload files」，把整個資料夾拖進去即可保留路徑；
   - 或用 git 指令：
       git clone <你的repo網址>
       cd <repo>
       mkdir -p .github/workflows
       # 把 shopline_daily_summary.py 複製到根目錄
       # 把 shopline-daily-report.yml 複製到 .github/workflows/
       git add .
       git commit -m "add shopline daily report workflow"
       git push

3. 設定兩組 Secrets（重要：不要把 token 直接寫進程式碼裡）：
   到 repo 的 Settings -> Secrets and variables -> Actions -> New repository secret，新增兩個 secret：
     名稱：SHOPLINE_TOKEN   值：(貼上你自己的 Shopline API token)
     名稱：LINE_TOKEN       值：(貼上你自己的 LINE Channel access token)
   這兩組值就是你原本設定 Claude 排程任務時用的那兩組 token，請從你自己保存的地方複製貼上，
   不要把它們寫進程式碼或任何檔案裡，只存在 GitHub Secrets 裡即可（Secrets 存進去之後畫面上
   不會再顯示明碼）。

4. 到 repo 的 Actions 分頁，確認 workflow「Shopline Daily Report to LINE」出現且已啟用（新 repo 通常預設就是啟用的）。

5. 先手動測試一次，不要直接等排程：
   - 到 Actions -> 選「Shopline Daily Report to LINE」-> 右邊「Run workflow」
   - period 選 today 或 yesterday，dry_run 打勾（true）
   - 按 Run workflow，跑完後點進去看 log，確認數字、TOP5 商品都正確
   - 確認沒問題後，可以再手動跑一次，這次把 dry_run 取消勾選，測試真的能收到 LINE 廣播

6. 排程時間已經照你原本在 Claude 設定的時間換算好：
   - 07:00 UTC＝台北時間 15:00 -> 自動用 --period today（今日即時業績）
   - 16:02 UTC＝台北時間隔天 00:02 -> 自動用 --period yesterday（昨日完整日報）
   這兩個排程都會「真的送出」LINE 廣播（沒有 --dry-run），完全不需要人工核准，
   之後每天會自動執行。

注意事項
--------
- GitHub Actions 的排程時間可能會有幾分鐘的延遲（官方排程機制本來就不是絕對準時），
  對每日報表來說通常沒有影響。
- 一旦部署到這裡，就完全脫離 Claude 的安全審查機制，數字算錯或程式邏輯有 bug
  都會直接廣播出去，沒有人會事先攔下來，建議部署後留意前幾天的執行結果
  （Actions 分頁可以看到每次執行的 log 與成功/失敗狀態，失敗時 GitHub 預設會寄信通知 repo 擁有者）。
- 如果之後想暫停，只要到 Actions 分頁把該 workflow 停用（Disable workflow）即可，
  不需要刪除 repo 或檔案。
