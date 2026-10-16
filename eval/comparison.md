# Model karşılaştırması

Her soruda bilgi bir kez toplandı; modeller aynı maddelerden yanıt yazdı.

| Model | Doğru |
|---|---|
| qwen/qwen3.8-27b | 12/12 |
| openai/gpt-oss-120b | 11/12 |
| gemini | 10/12 |

## annual-leave-5-years

**Soru:** 5 yıldır çalışıyorum, kaç gün yıllık izin hakkım var?

### qwen/qwen3.8-27b: GEÇTİ, 1.2 sn

Şirketimizde 5 yıldır çalıştığınız için yıllık izin hakkınız 14 iş günüdür.

### openai/gpt-oss-120b: GEÇTİ, 2.6 sn

Beş yıla kadar (beş yıl dahil) çalışan personel için 14 iş günü yıllık izin hakkı vardır (5.7.4.1). Ancak beş‑on beş yıl arası (on beş yıl dahil) çalışanlar için 20 iş günü olduğu da belirtilmiştir (5.7.4.2). Bu iki madde 5 yıllık hizmet süresi için çakıştığından, şirketinizin hangi maddeyi uyguladığını netleştirmeniz gerekir.

### gemini: GEÇTİ, 4.8 sn

Şirketteki hizmet sürenize göre yıllık izin süreniz beş yıla kadar (beş yıl dahil) olanlar için on dört iş günüdür. Yıllık izne hak kazanabilmeniz için Şirkette bir tam yıl çalışmış olmanız gerekmektedir.

## marriage-leave

**Soru:** Evlenirsem kaç gün izin alırım?

### qwen/qwen3.8-27b: GEÇTİ, 0.4 sn

Evlenmeniz halinde 3 gün mazeret izni hakkınız bulunmaktadır.

### openai/gpt-oss-120b: GEÇTİ, 0.9 sn

Evlenmeniz durumunda üç gün mazeret izni alabilirsiniz.

### gemini: GEÇTİ, 5.3 sn

Evlenmeniz halinde üç gün izin alabilirsiniz.

## probation-period

**Soru:** Deneme süresi ne kadar?

### qwen/qwen3.8-27b: GEÇTİ, 0.4 sn

Deneme süresi 2 aydır.

### openai/gpt-oss-120b: GEÇTİ, 0.9 sn

Deneme süresi 2 aydır.

### gemini: GEÇTİ, 23.0 sn

Deneme süresi 2 aydır.

## weekly-working-hours

**Soru:** Haftada kaç saat çalışıyoruz?

### qwen/qwen3.8-27b: GEÇTİ, 0.5 sn

Haftalık çalışma süreniz genel olarak 45 saattir. Ancak çalıştığınız pozisyona ve yürütülen hizmetlere göre bu süre geçmemek üzere farklı çalışma saatleri uygulanabilir.

### openai/gpt-oss-120b: GEÇTİ, 0.9 sn

Haftalık çalışma süreniz genel olarak 45 saattir.

### gemini: GEÇTİ, 13.2 sn

Personelin haftalık çalışma süresi genel olarak 45 saattir. Belli pozisyonlarda istihdam edilen personel için, yürütülen hizmetler dikkate alarak bu süreyi geçmemek üzere farklı çalışma saatleri uygulanabilir.

## bereavement-leave

**Soru:** Annem vefat etti, kaç gün izin kullanabilirim?

### qwen/qwen3.8-27b: GEÇTİ, 0.7 sn

Annemin vefatı nedeniyle 3 gün mazeret izni kullanabilirsiniz.

### openai/gpt-oss-120b: GEÇTİ, 1.4 sn

Annenizin vefatı durumunda mazeret izni kapsamında üç gün izin kullanabilirsiniz.

### gemini: GEÇTİ, 15.8 sn

Annenizin vefatı halinde üç gün mazeret izni kullanabilirsiniz.

## child-marriage-leave

**Soru:** Kızım evleniyor, izin alabilir miyim?

### qwen/qwen3.8-27b: GEÇTİ, 0.5 sn

Evet, kızınızın evlenmesi halinde 2 gün mazeret izni kullanabilirsiniz.

### openai/gpt-oss-120b: GEÇTİ, 1.8 sn

Evet, kızınızın evliliği nedeniyle 2 gün mazeret izni alabilirsiniz.

### gemini: GEÇTİ, 7.8 sn

Çocuğunuzun evlenmesi halinde iki gün mazeret izni alabilirsiniz.

## birth-leave-both-parents

**Soru:** Karım doğum yaptı, ikimiz ne kadar izin alabiliriz?

### qwen/qwen3.8-27b: GEÇTİ, 0.8 sn

Eşinizin doğum yapması durumunda, siz (baba) 3 gün mazeret izni kullanabilirsiniz. Eşiniz (anne) ise doğumdan önce 8 hafta ve doğumdan sonra 8 hafta olmak üzere toplam 16 hafta ücretli doğum izni hakkına sahiptir. Ayrıca çocuğu 1 yaşına gelene kadar günde 1,5 saat süt izni kullanabilir; bu izinler talebi halinde haftalık, aylık veya toplu olarak kullanılabilir. Eşiniz ayrıca isteği halinde en fazla 6 aya kadar ücretsiz izin de alabilir.

### openai/gpt-oss-120b: GEÇTİ, 3.4 sn

Doğum izni konusunda iki farklı hak söz konusudur. Çalışan olarak siz, eşinizin doğum yapması nedeniyle 5.7.5.1.1 maddesinde belirtilen üç günlük mazeret izni alabilirsiniz. Eşiniz de şirket çalışanı ise, 5.7.5.1 maddesine göre doğumdan önce sekiz hafta, doğumdan sonra da sekiz hafta olmak üzere toplam on altı haftalık doğum izni kullanabilir. Ayrıca, 5.7.8.3 maddesinde yer alan ücretsiz izin kapsamında, doğum yapan personel isteği üzerine en fazla altı aya kadar ücretsiz izin talep edebilir. Doğum izni süresinin ardından, çocuğun bir yaşına kadar günde bir buçuk saat süt izni de verilir.

Yönetmelikte şu konularda bilgi bulunmuyor: Eşin şirket çalışanı olup olmadığı. Detaylı bilgi için İnsan Kaynakları birimine başvurabilirsiniz.

### gemini: KALDI (missing: [['1,5', 'bir buçuk']]), 9.2 sn

Eşinizin doğum yapması halinde size üç gün mazeret izni verilir. Doğum yapan personel için ise doğum yapmasından önce sekiz hafta ve doğum yaptığı tarihten itibaren sekiz hafta doğum izni verilir; ayrıca isteği halinde en çok altı aya kadar ücretsiz izin verilebilir.

## meal-card-not-in-document

**Soru:** Yemek kartına ne kadar yükleniyor?

### qwen/qwen3.8-27b: GEÇTİ, 10.0 sn

Bu konuda bilgim yok. Detaylı bilgi için İnsan Kaynakları birimine başvurabilirsiniz.

### openai/gpt-oss-120b: GEÇTİ, 7.5 sn

Bu konuda bilgim yok. Detaylı bilgi için İnsan Kaynakları birimine başvurabilirsiniz.

### gemini: GEÇTİ, 28.5 sn

Bu konuda bilgim yok. Detaylı bilgi için İnsan Kaynakları birimine başvurabilirsiniz.

## company-car-not-in-document

**Soru:** Şirket bana araç veriyor mu?

### qwen/qwen3.8-27b: GEÇTİ, 1.0 sn

Yükümlülükler bölümünde, görevi nedeniyle kendisine teslim edilen araç ve gereçleri korumak, yetki verilen yerler dışına çıkarmamak ve görevi sona erdiğinde geri vermekten sorumlu olduğunuz belirtilmektedir. Bu ifade, görev gereği size araç teslim edilebileceğini göstermektedir; ancak hangi pozisyonlara veya koşullarda araç verildiğine dair spesifik bir liste veya kural metinde yer almamaktadır.

Yönetmelikte şu konularda bilgi bulunmuyor: Araç tahsisinin yapılacağı pozisyonlar, Araç tahsis koşulları ve süreleri. Detaylı bilgi için İnsan Kaynakları birimine başvurabilirsiniz.

### openai/gpt-oss-120b: GEÇTİ, 1.8 sn

Şirketin size araç verip vermediği düzenlemede açıkça belirtilmemiştir. Ancak 5.6.1.3 maddesinde, görevi nedeniyle kendisine teslim edilen araç, belge vb. malzemeleri korumak ve görev sona erdiğinde iade etmekle yükümlü olduğunuz belirtilmiştir. Bu, şirketin gerektiğinde araç temin edebileceğini, ancak her çalışan için zorunlu olmadığını gösterir.

Yönetmelikte şu konularda bilgi bulunmuyor: Araç temini politikası. Detaylı bilgi için İnsan Kaynakları birimine başvurabilirsiniz.

### gemini: GEÇTİ, 12.1 sn

Bu konuda bilgim yok. Detaylı bilgi için İnsan Kaynakları birimine başvurabilirsiniz.

## pregnancy-leave-and-severance

**Soru:** çok heycanlıyım karım gebe, o da burada çalışıyor, biz ne kadar izin alacağız ve karım gebelikten sonra ayrılacak tazminatını hesaplar mısın

### qwen/qwen3.8-27b: GEÇTİ, 1.6 sn

Eşinizin doğum yapması halinde size 3 gün mazeret izni verilir. Eşiniz için ise doğumdan önce 8 hafta ve doğumdan sonra 8 hafta doğum izni uygulanır. Ayrıca çocuğu 1 yaşına gelene kadar günde 1,5 saat süt izni hakkı vardır; bu izinler talebi halinde haftalık, aylık veya toplu olarak kullanılabilir. Eşiniz doğum izninin ardından isteği halinde en fazla 6 aya kadar ücretsiz izin alabilir. Eşinizin işten ayrılması durumunda alacağı tazminat miktarı hakkında bilgi verilemez.

Yönetmelikte şu konularda bilgi bulunmuyor: Eşinizin işten ayrılması durumunda alacağı tazminat miktarı. Detaylı bilgi için İnsan Kaynakları birimine başvurabilirsiniz.

### openai/gpt-oss-120b: KALDI (missing: [['3', 'üç']]), 3.1 sn

Karınızın doğum izni, doğumdan önce 8 hafta ve doğumdan sonra 8 hafta olmak üzere toplam 16 hafta ücretli mazeret izni olarak verilir. Çocuğun bir yaşına kadar her gün 1,5 saat süt izni kullanılabilir; bu saatler haftalık, aylık ya da toplu olarak talep edilebilir. Ayrıca, karınız isteği üzerine ücretsiz olarak en fazla 6 aya kadar ek izin alabilir.
Tazminat hesabı için gerekli bilgiler (örneğin hizmet süresi, brüt maaş vb.) sağlanmadığından hesaplama yapılamamaktadır.

Yönetmelikte şu konularda bilgi bulunmuyor: tazminat hesaplaması için gerekli bilgiler (hizmet süresi, brüt maaş vb.). Detaylı bilgi için İnsan Kaynakları birimine başvurabilirsiniz.

### gemini: KALDI (missing: [['1,5', 'bir buçuk', 'birbuçuk']]), 16.1 sn

Eşinizin doğum yapması halinde üç gün izin alabilirsiniz. Doğum yapan personele doğum yapmasından önce sekiz hafta ve doğum yaptığı tarihten itibaren sekiz hafta doğum izni verilir. Ayrıca doğum yapan personele isteği halinde en çok altı aya kadar ücretsiz izin verilebilir.

Yönetmelikte şu konularda bilgi bulunmuyor: tazminat hesaplaması. Detaylı bilgi için İnsan Kaynakları birimine başvurabilirsiniz.

## leave-balance-mid-seniority

**Soru:** Bu yıl kaç gün yıllık iznim kaldı?

### qwen/qwen3.8-27b: GEÇTİ, 0.5 sn

Mehmet Bey, bu yıl için kalan yıllık izin hakkınız 8 iş günüdür.

### openai/gpt-oss-120b: GEÇTİ, 1.9 sn

Kalan yıllık izin gün sayınız 8 gündür.

### gemini: GEÇTİ, 10.1 sn

Bu yıl kalan yıllık izin süreniz 8 gündür.

## leave-balance-not-eligible

**Soru:** Yıllık izne çıkabilir miyim?

### qwen/qwen3.8-27b: GEÇTİ, 0.6 sn

Hayır, şu an yıllık izne çıkamazsınız. Yıllık izne hak kazanabilmek için şirkette bir tam yıl çalışmış olmanız gerekmektedir. Kayıtlarınıza göre 1 Ağustos 2026'da göreve başladınız ve henüz bir tam yıl hizmet sürenizi doldurmadınız. Bu nedenle bu yıl için kullanabileceğiniz yıllık izin hakkınız bulunmamaktadır.

### openai/gpt-oss-120b: GEÇTİ, 1.8 sn

Maalesef, şirket politikamıza göre yıllık izin hakkı kazanabilmek için tam bir yıl çalışmış olmanız gerekir. Zeynep Hanım henüz bir yıl çalışmadığınız için bu yıl yıllık izne çıkma hakkınız bulunmamaktadır.

### gemini: GEÇTİ, 2.4 sn

Yıllık izne hak kazanabilmeniz için Şirket de bir tam yıl çalışmış olmanız gerekmektedir. Kayıtlarınıza göre Şirkette henüz bir tam yıl çalışmadığınız için henüz yıllık izne hak kazanmamış bulunuyorsunuz.
