# Three-task project pilot — 2026-09-18

These are assistant-authored, user-approved synthetic tasks. Runs use the existing project retrieval and answer-generation components, not a timed human UI trial. ChatGPT file-upload results are pending. No superiority is established.

## Initial findings

1. Remembered line: the correct source is Shabad DJQ, Ang 6, line shabados:UNDR. Neither initial keyword nor hybrid top eight included DJQ. Generated answer was rejected with ValueError by the generation/validation path. A separate diagnostic phrase-only lexical search for `mann jeetay jag jeet` ranked DJQ first. This is a reformulation result, not an initial-query success.

2. Helping without pride: generation succeeded but acknowledged no direct passage addressing pride in generosity. Retrieved snippets support only an indirect synthesis. Relevance and interpretive support remain ungraded; citation validity is not proof of relevance.

3. Hukam context: correct exact line is shabados:H0PC, Shabad DMP, Ang 1. Hybrid retrieval missed DMP, and the generated answer explicitly said it lacked the requested immediate context. Phrase-only lexical `hukam rajai chalna` still missed the target in its top three; corpus spelling `hukam rajaaee chalanaa` ranked DMP first.

## Engineering observations

The same natural-language question is sent directly into retrieval, so framing words can overwhelm a remembered quote. Roman Punjabi spelling normalization is incomplete. The generator receives selected individual source lines, not the full passages available to the reader; contextual interpretation therefore has less evidence than the UI can display. These observations motivate improvements but do not establish which component change will fix the broader task distribution. Freeze these results before changes and evaluate future fixes on new examples as well.

## Recorded outputs

### pilot-01

I remember something like “mann jeetay jag jeet.” Find the original line, its English translation, and the surrounding passage.

Generated: False; model: gpt-5.6-terra; component-run elapsed: 8.634 seconds. Timing includes diagnostic keyword retrieval and is not human completion time.

Error class: ValueError

Retrieved source lines:

- Shabad 26R, Ang 971, shabados:BYV4: Meditate, meditate in remembrance on the Lord, Har, Har, and sing His Praises in your mind.
- Shabad F7C, Ang 632, shabados:8ES4: Meditating on Him in remembrance, Ganika the prostitute was saved; enshrine His Praises within your heart. ||1||Pause||
- Shabad TF7, Ang 263, shabados:MUWM: Remember, remember in meditation the Lord, the Creator, the Cause of causes.
- Shabad K7X, Ang 263, shabados:U8ET: Those who remember God - to them, I am forever a sacrifice.
- Shabad XHM, Ang 499, shabados:PNP4: O Lord Master, wherever I remember You, there I find You.
- Shabad 1US, Ang 263, shabados:HRC3: The peace of the meditative remembrance of God has no end or limitation.
- Shabad E44, Ang 1007, shabados:QN0E: Meditating in remembrance forever on the Lord, Har, Har, O Nanak, countless beings have been saved. ||2||6||29||
- Shabad BVX, Ang 1352, shabados:PQMZ: Meditate in remembrance on the Lord - meditate on the Lord; this alone shall be of use to you.

### pilot-02

Find passages about helping other people without becoming proud of how generous or good you are. Explain how the passages relate to that tension.

Generated: True; model: gpt-5.6-terra; component-run elapsed: 59.952 seconds. Timing includes diagnostic keyword retrieval and is not human completion time.

The supplied passages support helping and good conduct, while warning against self-importance and self-reliance. They do not directly mention pride in generosity, but they frame any human action as dependent on God’s power and distinguish good deeds from the ego of religious display.

- Guru Nanak Dev Ji’s line says, in the supplied English translation, “Without good deeds, it becomes more and more deficient.” This supports the importance of good action, which can include care for others, although the line itself does not specifically name generosity or charity. [shabados:4.8.7:line:2YXZ]
- Guru Nanak Dev Ji also warns that people may repeatedly read religious books yet continue in error because they are “so proud of their religious robes,” in the supplied translation. This directly cautions against pride attached to outward religious identity or appearance. [shabados:4.8.7:line:1NJ0]
- Guru Arjan Dev Ji’s line asks, “but without God's Power, what can anyone do?” The supplied translation can be read as placing human capacity—including the capacity to do good—under God’s power rather than personal self-credit. [shabados:4.8.7:line:7NKN]
- A closely related line, also attributed here to Guru Arjan Dev Ji, says, “Without the Transcendent Lord, what can anyone do?” This reinforces humility: a person should not treat good action as proof of independent greatness. [shabados:4.8.7:line:GCT7]
- The line stating that one is not saved by “hundreds of thousands and millions of helping hands” limits what help from people can accomplish spiritually, according to the supplied English translation. Thus, helping others is not presented as a basis for pride or as a guarantee of one’s own salvation. [shabados:4.8.7:line:QXKT]
- Taken together, the passages hold the tension this way: good deeds matter, but pride is shown as a source of error, and the power or ultimate outcome of action is not credited to the individual alone. Therefore, one may help others while avoiding the thought that generosity makes one spiritually superior. [shabados:4.8.7:line:2YXZ, shabados:4.8.7:line:1NJ0, shabados:4.8.7:line:7NKN, shabados:4.8.7:line:QXKT]

Caveat: None of the supplied passages explicitly says “help others without being proud of your generosity.” The connection to generosity is an application of their statements about good deeds, pride, dependence on God’s power, and the limits of human help; the English wording quoted above is from the supplied translations.

Retrieved source lines:

- Shabad 1NJ, Ang 282, shabados:7NKN: but without God's Power, what can anyone do?
- Shabad N2K, Ang 61, shabados:1NJ0: Reading their books over and over again, people continue making mistakes; they are so proud of their religious robes.
- Shabad T0Y, Ang 264, shabados:QXKT: You shall not be saved by hundreds of thousands and millions of helping hands.
- Shabad 22S, Ang 56, shabados:2DUA: Without the Guru, they are not released from their karma, although they speak and listen and preach and explain. ||7||
- Shabad AD1, Ang 25, shabados:2YXZ: Without good deeds, it becomes more and more deficient. ||3||
- Shabad YY6, Ang 218, shabados:GCT7: Without the Transcendent Lord, what can anyone do? Cursed is his life, and cursed his reputation. ||1||
- Shabad MGM, Ang 655, shabados:KGT1: People say it is good to live forever,
- Shabad M2T, Ang 334, shabados:CPDZ: And those, to whom I go to find release - they themselves are bound by all sorts of chains. ||1||Pause||

### pilot-03

People translate “hukam rajai chalna” as accepting God’s will. Does the surrounding passage suggest being passive, or something different? Show the source and distinguish the translation from your interpretation.

Generated: True; model: gpt-5.6-terra; component-run elapsed: 15.744 seconds. Timing includes diagnostic keyword retrieval and is not human completion time.

The exact phrase “ਹੁਕਮਿ ਰਜਾਈ ਚਲਣਾ / hukam rajaaee chalnaa” and its surrounding lines are not included in the supplied passages. Therefore, these sources cannot establish what that specific passage’s immediate context says about passivity. In the supplied verses, however, Hukam is described not only with translation words such as “accepting,” but also as something to “understand,” “obey,” and in one verse alongside “serving the Lord.” This language supports reading acceptance as an engaged spiritual orientation rather than mere inactivity, though that is an interpretation of the supplied translations, not a direct translation of the exact phrase.

- The supplied English translations render related expressions as “accepts God’s Will,” “accepting it,” and “accepts the Will of the Lord.” Those are the translators’ English choices for the cited Gurbani lines; they do not themselves use the word “passive.” [shabados:4.8.7:line:Y8P0, shabados:4.8.7:line:ATYF, shabados:4.8.7:line:KWFC]
- Other supplied translations use active terms: the Gurmukh “understands” Hukam; one who does not obey Hukam experiences the Lord as far away; and a line says that without serving the Lord there is pain, while accepting Hukam removes pain. [shabados:4.8.7:line:D4JM, shabados:4.8.7:line:GZX3, shabados:4.8.7:line:NMG8]
- On that textual basis, an interpretation is that accepting Hukam is not presented simply as doing nothing: it is connected with becoming Gurmukh, understanding, obeying, and serving. The passages also connect this acceptance with peace, the Lord’s essence, and devotion. [shabados:4.8.7:line:Y8P0, shabados:4.8.7:line:ATYF, shabados:4.8.7:line:KWFC, shabados:4.8.7:line:NMG8]
- The supplied text also describes Hukam as pervasive and says that all things happen by it. That statement can frame acceptance of a reality larger than oneself, but these excerpts alone do not spell out how a person should act in every practical situation. [shabados:4.8.7:line:5360]

Caveat: The exact line “hukam rajai chalna” and the verses immediately before and after it were not supplied. So I cannot give a source-based reading of its surrounding passage specifically, or claim that the passages settle the question of passivity in every sense.

Retrieved source lines:

- Shabad 810, Ang 556, shabados:D4JM: O Nanak, the Gurmukh understands the Hukam of the Lord's Command; the Lord showers His Mercy upon him. ||1||
- Shabad 1YA, Ang 1128, shabados:5360: The Hukam of the Lord's Command is pervasive; by the Hukam of His Command, all things happen. ||1||Pause||
- Shabad G05, Ang 510, shabados:GZX3: O Nanak, if one does not obey the Hukam of the Lord's Command, then within one's own home, the Lord seems far away.
- Shabad EXC, Ang 1093, shabados:6JTD: By the Pleasure of His Will, the Lord inspires us to obey the Hukam of His Command; by the Pleasure of His Will, we find peace.
- Shabad HKR, Ang 1246, shabados:Y8P0: One who becomes Gurmukh accepts God's Will; he intuitively drinks in the Lord's sublime essence.
- Shabad 5UR, Ang 948, shabados:ATYF: The Hukam, the Command of the One Lord is all-pervasive; accepting it, peace is found. ||3||
- Shabad EXG, Ang 1091, shabados:NMG8: Without serving the Lord, he suffers in pain; accepting the Hukam of God's Command, pain is gone.
- Shabad NDU, Ang 950, shabados:KWFC: O Nanak, one who accepts the Will of the Lord is His devotee. Without accepting it, he is the falsest of the false. ||1||
