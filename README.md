# npm Paketleri Icin 3B Sosyal Ag Analizi

Bu proje, secilen bir npm paketinin bagimliliklarini npm registry uzerinden cekip `NetworkX` ile graph yapisina donusturur. Iki farkli gosterim yolu vardir:

- `matplotlib` ile canli ve surekli donen 3B animasyon
- `FastAPI` ile paket adini gonderip tarayicida surekli donen 3B ag sayfasi

## Ne yapiyor?

- npm registry uzerinden paket bilgisini ceker.
- Bagimliliklarin bagimliliklarini da dahil ederek daha genis bir graph kurar.
- Her paketi bir dugum, bagimlilik iliskisini bir kenar olarak modele ekler.
- Paket isimlerini node etiketleri olarak gosterir.
- `NetworkX` ile degree centrality, eigenvector centrality, betweenness centrality, closeness centrality ve ag yogunlugu yuzdesini hesaplar.
- 20-30 node civarinda daha karmasik bir ag uretmek icin varsayilanlari daha genis tutar.

## Kurulum

Bu calisma alaninda gerekli paketler kuruldu:

- `networkx`
- `numpy`
- `scipy`
- `matplotlib`
- `pillow`
- `requests`
- `fastapi`
- `uvicorn`

## 1. Canli Matplotlib Animasyonu

Asagidaki komut `express` paketi icin pencere acar. Bu pencere GIF gibi basa sarmaz; surekli doner.

```bash
c:/Users/cihan/OneDrive/Masaüstü/SocialNetworkAnalysis/.venv/Scripts/python.exe npm_dependency_3d.py express --depth 3 --max-children 8 --max-nodes 30
```

Kayit almak isterseniz yine GIF uretebilirsiniz, ama GIF dogasi geregi bir noktada basa sarar:

```bash
c:/Users/cihan/OneDrive/Masaüstü/SocialNetworkAnalysis/.venv/Scripts/python.exe npm_dependency_3d.py webpack --depth 3 --max-children 8 --max-nodes 30 --frames 360 --interval 40 --save output/webpack_dependencies.gif --no-show
```

## 2. FastAPI Ile Paket Gonderme

Sunum icin daha kullanisli yol budur. Paket adini formdan gonderebilir, 3B agi tarayicida gorebilir ve grafigi mouse ile dondurup yakinlastirabilirsiniz.

Sunucuyu baslatin:

```bash
c:/Users/cihan/OneDrive/Masaüstü/SocialNetworkAnalysis/.venv/Scripts/python.exe -m uvicorn fastapi_app:app --reload
```

Sonra tarayicida su adresi acin:

```text
http://127.0.0.1:8000
```

API olarak yalnizca graph verisini almak isterseniz:

```text
http://127.0.0.1:8000/api/graph?package_name=express&depth=3&max_children=8&max_nodes=30
```

Donen JSON icinde `metrics` alani vardir. Bu alanda ag yogunlugu yuzdesi ile degree, eigenvector, betweenness ve closeness centrality sonuclari bulunur.

## Sunum Icin Not

- `express`, `webpack`, `vite`, `eslint` gibi paketler genelde daha dolu graph verir.
- `depth=3`, `max_children=8`, `max_nodes=30` sunum icin iyi bir baslangictir.
- FastAPI sayfasinda grafigi sol tik ile dondurebilir, mouse tekerlegi ile zoom yapabilirsiniz.
- FastAPI sayfasinda ag yogunlugu, kok paketin tum merkeziyetleri ve en merkezi paketlerin listesi de gosterilir.
- Node isimleri kalabaliklasirsa `max_nodes` degerini 24-30 araliginda tutun.
- Matplotlib calistirmasinda ayni metrikler grafik uzerinde ve terminal cikisinda yazdirilir.

## Teknik Not

`NetworkX` dogrudan tam ozellikli bir 3B renderer saglamaz. Bu projede 3 boyutlu node konumlari `NetworkX spring_layout(dim=3, method="energy")` ile uretilir. Masaustu gosterimi `matplotlib`, web gosterimi ise `FastAPI` uzerinden cagrilan Plotly istemci cizimi ile yapilir.
