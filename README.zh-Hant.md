<p align="center">
  <img src="https://raw.githubusercontent.com/DAB-LABS/HAIR/main/images/HAIR-readme-hero-v0.2.png" alt="HAIR 橫幅" width="900" />
</p>

# HAIR

**HAIR 把您的紅外線碼從廠商雲端、發射器記憶體和設定檔中解放出來，帶進 Home Assistant。**

把任何遙控器對準紅外線接收器按下按鈕，HAIR 就會把這個訊號變成 Home Assistant 真正用得上的東西：可以放在任何儀表板上的按鈕、自動化的觸發器，以及能透過 HA 原生紅外線平台上任何發射器送出的指令。不用 YAML，不用廠商 App，也不必把碼學習到別人家的盒子裡。

## 安裝

[![Open your Home Assistant instance and open the HAIR repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=DAB-LABS&repository=HAIR&category=integration)

1. 開啟 HACS 並搜尋 HAIR
2. 安裝 HAIR，重新啟動 Home Assistant，然後在「設定 → 裝置與服務」中新增此整合

需要 Home Assistant 2026.6 或更新版本。

## 取得紅外線碼的五種方式

- **嗅出來（Sniffer）。** 按下實體遙控器上的按鈕，HAIR 會即時從空中擷取訊號、建立指紋，並依遙控器分組。
- **剪下來（Clipper）。** 貼上已知的紅外線碼，或選擇品牌與型號，從內建碼庫填滿一整支遙控器。
- **拔出來（Plucker）。** 把廠商發射器（例如 Tuya Local）中已學習的碼取出來，不必在接收器上重新學一次。
- **聽出來（Mirror）。** 透過 Home Assistant 發出的每個紅外線指令都會出現在 Mirror 中，不論是否有接收器聽到，點一下就能變成您自己的指令。
- **穿上它（衣櫥）。** 把碼檔拖進衣櫥 -- 別人分享的碼組（Wig）、SmartIR 的 JSON、Flipper Zero 的 `.ir`、LIRC 設定檔、IrScrutinizer 匯出的 Girr、Logitech Harmony 裝置檔、Global Cache 碼組、Tasmota 紅外線碼或 irdb 的 CSV -- 它會掛進您的收藏，點一下就能變成可用的遙控器。

## 有了碼之後能做什麼

- **建立裝置。** 為電視、冷氣、風扇、燈光、開關或布幕建立檔案，把擷取到的訊號指派為指令，HAIR 就會自動建立對應的原生實體：電視成為真正的媒體播放器，冷氣成為具備模式與溫度預設的真正空調實體，風扇則有風速控制。它們在儀表板、腳本和語音助理中，就和其他 Home Assistant 裝置一樣運作。
- **把遙控器按鍵變成觸發器。** 任何實體遙控器上的任何按鍵都能觸發自動化。按下舊電視遙控器上的紅色按鈕，就能啟動電影之夜情境。觸發器知道是哪個房間聽到這次按壓，所以同一支遙控器在不同房間可以做不同的事。沒有其他整合做得到。
- **盯著 Mirror。** 即時稽核家中發出的所有訊號：送出了哪個指令、經由哪個發射器、又被哪個接收器聽到。半夜兩點紅外線出了什麼怪事，Mirror 都看在眼裡。
- **測試並打磨一切。** 在信任一個訊號之前，先從任一發射器試發；為訊號取別名；直接編輯 Pronto 碼；並讓 HAIR 解碼它認得的協定（NEC、Sony、RC-5、Samsung 等），以更乾淨的方式發送。
- **試戴（Fitting）。** 在真實硬體上驗證碼組：把它採用為裝置、實際用一陣子，存回衣櫥時逐一確認哪些訊號真的有效。簽署過的試戴紀錄會寫在碼組檔案裡，跟著分享出去；完全驗證過的碼組會在衣櫥中顯示綠色勾號。

面板會說您的語言：英文、西班牙文、法文、日文、德文、波蘭文、葡萄牙文、荷蘭文、義大利文、俄文、簡體中文與繁體中文，並自動跟隨您 Home Assistant 個人資料的語言。

> [!IMPORTANT]
> HAIR 面板的繁體中文翻譯（以台灣用語為準）由程式設計助理起草，正在等待母語使用者審閱。如果您願意接手：審閱只需要一個 pull request，您的名字會寫進檔案裡。從這裡開始：[Adding a language](CONTRIBUTING.md#adding-a-language)

## 完整文件

包含設定用 YAML、支援的硬體、功能指南與螢幕截圖的完整 README 為英文版：

**[閱讀完整文件](README.md)**

---

*譯自英文 README，對應 v1.3.1。本檔案由程式設計助理起草，並隨每次發布更新。歡迎母語使用者接手，詳見 [Adding a language](CONTRIBUTING.md#adding-a-language)。*
