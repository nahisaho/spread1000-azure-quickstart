"""多言語コーパスサンプル (パブリックドメイン抜粋 + オリジナル要旨)

言語横断検索デモ用に、日本語/英語/フランス語/ドイツ語/中国語の
短文を用意 (すべて公共文献の要旨相当のオリジナル文)。
"""

CORPUS: list[dict] = [
    {"id": "ja01", "lang": "ja", "text": "源氏物語は平安時代中期に紫式部によって書かれた長編物語で、光源氏の恋愛と人生を描く。"},
    {"id": "ja02", "lang": "ja", "text": "枕草子は清少納言による随筆で、宮廷生活の観察と美意識が記されている。"},
    {"id": "ja03", "lang": "ja", "text": "俳句は五・七・五の音節構造を持つ日本の短詩形で、季語を含むのが伝統である。"},
    {"id": "ja04", "lang": "ja", "text": "夏目漱石の吾輩は猫であるは明治期の風刺小説で、猫の視点から人間社会を描く。"},

    {"id": "en01", "lang": "en", "text": "The Tale of Genji, written by Murasaki Shikibu in the Heian period, is often considered the world's first novel."},
    {"id": "en02", "lang": "en", "text": "Haiku is a traditional Japanese short poem consisting of three phrases with a 5-7-5 syllable pattern."},
    {"id": "en03", "lang": "en", "text": "Shakespeare's Hamlet, written around 1600, explores themes of revenge, madness, and mortality."},
    {"id": "en04", "lang": "en", "text": "Impressionism is a 19th-century art movement characterized by small, thin brushstrokes and emphasis on light."},

    {"id": "fr01", "lang": "fr", "text": "Le Genji Monogatari, écrit par Murasaki Shikibu à l'époque de Heian, est considéré comme l'un des premiers romans du monde."},
    {"id": "fr02", "lang": "fr", "text": "L'impressionnisme est un mouvement artistique français du XIXe siècle, avec Monet et Renoir parmi ses figures majeures."},

    {"id": "de01", "lang": "de", "text": "Goethes Faust ist ein tragisches Drama, das die Themen Wissen, Verlangen und moralische Verantwortung behandelt."},
    {"id": "de02", "lang": "de", "text": "Der Impressionismus ist eine französische Kunstströmung des 19. Jahrhunderts, die sich auf Lichteffekte konzentriert."},

    {"id": "zh01", "lang": "zh", "text": "《源氏物語》是日本平安時代紫式部所著的長篇小說，被稱為世界最早的小說之一。"},
    {"id": "zh02", "lang": "zh", "text": "俳句是一種源自日本的短詩，通常由五、七、五共十七個音節組成。"},
    {"id": "zh03", "lang": "zh", "text": "印象派是十九世紀法國興起的藝術運動，重視光線與色彩的即時捕捉。"},
]
