training_1 = """
Now analyze the learner's responses to the following training. 

Training Objectives:
- Différencier les types de céphalées
- Poser un diagnostic pertinent en contexte clinique complexe par la discrimination des caractéristiques cliniques de la migraine, des céphalées de tension et des céphalées médicamenteuses
- Évaluer de façon critique les options thérapeutiques aiguës, préventives et hormonales dans la prise en charge des migraines

Trainings Content:

Module 1 : Diagnostic et suivi de la migraine

<Situation 1>
Situation 1:
Vous voyez en clinique externe une nouvelle patiente de 25 ans dont la plainte principale est céphalée. Elle n’a pas d’autres antécédents médicaux, n’a pas d’antécédents familiaux pertinents et ne prend pas de médicaments sur une base régulière. 

<Scenario 1>
Scenario 1: 
Si vous pensiez ...
Migraine
Et qu’alors ...
Elle vous décrit la douleur comme étant souvent intense et incapacitante, pulsatile, plus souvent à gauche qu’à droite, accompagnée de photophobie et durant jusqu’à 24h sans traitement.

Experts' Responses:


Expert 2: 
Reponse: Renforcée
Justification: Les critères diagnostiques de la migraine épisodique sont rencontrés.

Expert 3: 
Reponse: Renforcée
Justification: Intensité, caractère unilat et changeant de côté, présence d'irritabilité à la lumière (pas de mention sonophobie), présence de nausée et limitée dans le temps, suggestif de migraine, l'exacerbation par activité simple n'est pas précisée ni la fréquence.

Expert 4: 
Reponse: Renforcée
Justification: On n'a pas idée de l'historique (depuis quand?), du mode d'apparition ni de la fréquence

Expert 5: 
Reponse: Renforcée
Justification: Elle a tous les critères de la migraine, mais faudrait quand même éliminer céphalées secondaires avec d’autres questions.

Expert 6: 
Reponse: Fortement renforcée
Justification: EMême si on manque de précisions quant à la fréquence, durée, évolution.

Learner's Response:
Reponse: Renforcée
Justification: Rempli critères ICHD pour ce que l'on sait (pas d'info si au moins 5 attaques, pas d'info si aura, pas d'info si examen neurologique normal)
</Scenario 1>

<Scenario 2>
Scenario 2:

Si vous pensiez ... 2- Céphalée de tension

Et qu’alors ... Elle vous décrit la douleur d’intensité modérée, serrative bilatérale, qui augmente au moindre effort, pas de photophobie mais souvent accompagnée de nausée. Sans traitement, peut durer jusqu’à 24h.

Experts' Responses:


Expert 2: Reponse: Fortement affaiblie 
Justification: L’augmentation au moindre effort, les nausées fréquentes ne vont pas avec le diagnostic de céphalées de tension.

Expert 3: Reponse: Fortement affaiblie 
Justification: Tous les critères pour migraine sont satisfaits: intensité modérée, augmente à l'effort, souvent nausée, durée 24h.

Expert 4: Reponse: Affaiblie 
Justification: Les nausées , la durée et l’intensité de la céphalée sont plutôt en faveur de migraine.

Expert 5: Reponse: Affaiblie 
Justification: La présence de nausée, l'augmentation aux efforts simples rend suggestif de migraine ainsi que la limitation dans le temps, la fréquence n'est pas précisée, serait instructif.

Expert 6: Reponse: Affaiblie 
Justification: La nausée est l'élément en défaveur du dx de migraine. Si l'intensité avait été jugée légère par la pte (élément subjectif par contre) la réponse aurait été "fortement affaiblie".

Learner's Response:
Reponse: Fortement affaiblie 
Justification: Semble beaucoup plus compatible avec migraine: aggravé par activité physique minime est présent avec nausée.
</Scenario 2>

<Scenario 3>
Scenario 3:

Si vous pensiez ... 3- Migraine

Et qu’alors ... Elle vous décrit la douleur comme étant bilatérale, pulsatile et sévère. Souvent pire le matin et accompagnée de nausée. Depuis 1 mois, la douleur peut la réveiller la nuit. Partiellement soulagée avec Acétaminophène ou AINS.

Experts' Responses:


Expert 2: Reponse: Affaiblie 
Justification: Début récent = à garder en tête pour causes secondaires de céphalée pire le matin = est-ce une céphalée orthostatique? (Serait plutôt céphalée secondaire: ex: hypertension intracrânienne... ) Peut la réveiller la nuit = est-ce céphalée orthostatique vs autre cause secondaire (ex: apnée du sommeil) ce cas est une céphalée secondaire jusqu'à preuve du contraire.

Expert 3: Reponse: Affaiblie 
Justification: Tout en étant suggestif de migraine, le caractère constant de la douleur avec augmentation la nuit, tel qu'il semble être selon le questionnaire devrait nous questionner sur la possibilité de céphalée secondaire.

Expert 4: Reponse: Affaiblie 
Justification: Ça pourrait en être, mais il manque des informations cliniques sur la durée et fréquence des épisodes et le tableau semble progressif et donc possiblement inquiétant pour céphalées secondaires.

Expert 5: Reponse: Affaiblie 
Justification: A les critères de migraine: pulsatile, sévère, nausée et même si pas dans les critères plusieurs personnes se lèvent avec la migraine mais possibles drapeaux rouges: pire le matin et réveil la nuit donc HTIC à éliminer.

Expert 6: Reponse: Renforcée 
Justification: "Depuis quelques mois" renforce certainement le dx d'une céphalée primaire bénigne, mais pas à 100%.

Learner's Response:
Reponse: Fortement affaiblie 
Justification: On retrouve ici des signes d’alerte pour une céphalée secondaire et la présence d’une hypertension intra crânienne (pire le matin, réveil nocturne, non soulagé avec les analgésiques).
</Scenario 3>
</Situation 1>

<Situation 2>
Situation 2: Vous voyez en clinique externe une patiente de 30 ans connue pour migraine. Elle a des crises de migraine depuis l’âge de 25 ans. Ses céphalées habituelles sont pulsatiles du côté droit d’intensité modérée à sévère et accompagnée de photophobie et de nausée. Elle prend des acétaminophènes et un sumatriptan au besoin. Elle n’a pas d’autres antécédents médicaux, n’a pas d’antécédents familiaux pertinents et ne prend pas de médicaments sur une base régulière. Elle a plus de céphalées depuis deux mois. Elle vient de changer de travail.

<Scenario 4>
Scenario 4:

Si vous pensiez à ... 1- Migraine exacerbée par le stress

Et qu’alors ... Elle vous indique que son sumatriptan n’est plus efficace.

Experts' Responses:


Expert 2: Reponse: Affaiblie Justification: La possibilité d'une céphalée par surutilisation de médicament abortif doit être envisagée (même si l'exacerbation est sur une période inférieure à 6 mois) se greffant sur une exacerbation associée au stress.

Expert 3: Reponse: Affaiblie Justification: Il faut questionner la consommation d’analgésiques et triptans pour éliminer céphalées d’origine médicamenteuse surajoutée.

Expert 4: Reponse: Affaiblie Justification: Je dois déterminer fréquence des crises pour éliminer COM. Le plus souvent le traitement de crise perd son efficacité lorsque pris régulièrement.

Expert 5: Reponse: Inchangée Justification: Il faudra mieux définir "échec au sumatriptan" avec la pte (moment de la prise, vomissements, etc.).

Expert 6: Reponse: Renforcée Justification: Besoin d'explorer autres habitudes de vie pouvant aggraver: sommeil, alimentation - jeûne, etc.

Learner's Response:
Reponse: Affaiblie 
Justification: On se serait plutôt attendu à une augmentation en fréquence des migraines, mais avec une réponse similaire au triptan. La patiente peut avoir développé un nouveau type de céphalée primaire, par exemple, des céphalées de tension, ou une céphalée secondaire.
</Scenario 4>

<Scenario 5>
Scenario 5:

Si vous pensiez à ... 5- Migraine exacerbée par le stress

Et qu’alors ... Elle vous indique que ses céphalées ne sont pas si différentes que d’habitude, excepté le fait qu’elles sont un peu plus bilatérales, surviennent plus au réveil et s’améliore au courant de la journée.

Experts' Responses:


Expert 2: Reponse: Affaiblie Justification: Pire le matin et s'améliore dans la journée pourrait être signe céphalée secondaire, donc besoin d'investiguer davantage avant de mettre uniquement sur le dos de la migraine, mais le fait que pas différent d'habitude est un peu rassurant.

Expert 3: Reponse: Affaiblie Justification: Tout patient avec migraine peut développer un autre type de céphalée (primaire ou secondaire). Ici, on pourrait soupçonner de l’apnée du sommeil.

Expert 4: Reponse: Inchangée Justification: Il serait intéressant de savoir à quelle fréquence les céphalées sont présentes, savoir aussi si elle est soulagée par sa médication. Intéressant de s'informer du type de travail, posture, tâche, conflit.

Expert 5: Reponse: Inchangée Justification: Idem , analgésiques et consommation de triptans ? Et facteur cervicogenique ? Posture au nouveau travail? Et questionner sommeil.

Expert 6: Reponse: Renforcée Justification: Aucun élément inquiétant ici qui ferait penser à une céphalée secondaire de mauvais augure.

Learner's Response:
Reponse: Fortement affaiblie 
Justification: Éliminer COM (le plus probable), et SAHS vu mieux au courant de la journée.
</Scenario 5>

<Scenario 6>
Scenario 6:

Si vous pensiez à ... 3- Céphalée médicamenteuse surajoutée

Et qu’alors ... Elle vous indique qu’elle prend des acétaminophènes environ un jour sur deux et un sumatriptan environ 4 fois par mois depuis environ six mois.

Experts' Responses:


Expert 2: Reponse: Renforcée Justification: En effet, elle prend un traitement aigu plus de 15 jours par mois depuis plus de 3 mois.

Expert 3: Reponse: Renforcée Justification: La fréquence d'utilisation d'analgésiques et d'abortifs à plus de 15j par mois ainsi que la période d'utilisation de plusieurs mois suggère une céphalée par surutilisation de médicaments.

Expert 4: Reponse: Renforcée Justification: Elle rencontre les critères diagnostiques de COM pour le nombre de jours/mois, mais pas ceux de la durée i.e. "depuis plus de 3 mois"...

Expert 5: Reponse: Fortement renforcée Justification: C.O.M acétaminophène. Il faut s’assurer techniquement qu’elle a effectivement au moins 15 jours de céphalées par mois et qu’elle ne prend pas d’acétaminophène pour d’autres raisons.

Expert 6: Reponse: Fortement renforcée Justification: Le fait que c'est pire le matin et s'améliore au courant de la journée, je ferai quand même questionnaire pour SAHS, mais COM le plus probable. 

Learner's Response:
Reponse: Inchangée 
Justification: Acetaminophen plus de 15 jours par mois est risque céphalée rebond, ici " environ 1 jour sur 2" est un peu vague, mais va dans la mauvaise direction et besoin de mieux clarifier (avec journal céphalée). Aussi est-ce que Suma le même jour qu'acétal ou autre jour?
</Scenario 6>
</Situation 2>
"""

training_2 = """
Now analyze the learner's responses to the following training. 

Training Objectives:
- Différencier les types de céphalées
- Poser un diagnostic pertinent en contexte clinique complexe par la discrimination des caractéristiques cliniques de la migraine, des céphalées de tension et des céphalées médicamenteuses
- Évaluer de façon critique les options thérapeutiques aiguës, préventives et hormonales dans la prise en charge des migraines

Trainings Content:

Module 2 : Traitement aigu et gestion des habitudes de vie de la migraine

<Situation 1>
Situation 1: Vous voyez en clinique externe une patiente connue pour migraines épisodiques. Elle fait en moyenne deux à trois crises de migraines par mois. Elle doit s’absenter du travail lorsqu’elle a une crise. Elle n’a pas d’antécédents familiaux pertinents.

<Scenario 1>
Scenario 1:

Si vous pensiez à ... 1- Suggérer de prendre Ibuprofène 400 mg PRN.

Et qu’alors ... La patiente vous dit qu’elle préfèrerait un traitement non pharmacologique

Experts' Responses:


Expert 2: Reponse: Affaiblie Justification: Il est possible de réduire la fréquence des migraines en contrôlant les facteurs déclencheurs (manque de sommeil, stress, jeûne) et en adoptant de saines habitudes de vie (alimentation, sommeil, exercice physique, relaxation).

Expert 3: Reponse: Affaiblie Justification: Il y a plusieurs options non-pharmaco a ne pas négliger, donc je suggérerais à la patiente de les tenter, et de considérer Ibu en seconde ligne si migraine progresse trop, mais en sachant que pharmaco fonctionne moins si pris trop tard.

Expert 4: Reponse: Affaiblie Justification: J’essaierais de discuter de ses préoccupations vs la médication,expliquer que vu la sévérité des crises ce serait difficile de trouver un soulagement de la crise non médicamenteux. On pourrait regarder les approches non médicamenteuses préventives pour tenter d’en diminuer la fréquence (déclencheurs, hygiène de vie), etc.

Expert 5: Reponse: Affaiblie Justification: C'est important de développer un lien de confiance avec la patiente. Je respecterais sa décision tout en questionnant sa réticence envers un traitement pharmacologique, surtout parce que l'intensité des crises l'empêche de travailler. Je proposerais un calendrier et qu'elle essaye d'identifier des déclencheurs et je discuterai des habitudes de vie qui peuvent influencer positivement la migraine. Suivi rapide après 1-2 mois pour rediscuter de la situation.

Expert 6: Reponse: Inchangée Justification: Faudra tenter de la convaincre que la migraine n'est pas une céphalée ordinaire.

Learner's Response:
Reponse: Affaiblie 
Justification: Je questionnerais plus sur les circonstances entourant la crise, proximité des règles, facteurs déclenchants, sommeil, alcool, stress, rythme repas, mais insisterait sur le traitement pharmaco, car il y a un degré d'incapacité significatif.
</Scenario 1>

<Scenario 2>
Scenario 2:

Si vous pensiez à ... 2- Débuter un triptan

Et qu’alors ... La patiente vous dit qu’elle a débuté récemment un citalopram pour dépression.

Experts' Responses:


Expert 2: Reponse: Inchangée Justification: Le risque de syndrome serotoninergique avec Triptan et ISRS est généralement surestimé. J'en avertis mes patients pour qu'ils sachent et puissent reconnaitre les Sx tôt, et discute des risques avec eux, mais cela ne m'a jamais empêché de prescrire des triptans.

Expert 3: Reponse: Inchangée Justification: Interactions triptan / ISRS surévaluées (overrated).

Expert 4: Reponse: Inchangée Justification: La réanalyse des données qui mettait en garde contre le syndrome serotoninergique avec cette association a été rassurante . Le fait d’ajouter un triptan à un antidépresseur n’augmente pas significativement le risque de synd. Sérotoninergique.

Expert 5: Reponse: Inchangée Justification: Risque de syndrome sérotonergique théoriquement possible, mais arrive que très rarement. Mieux de le mentionner quand même parce que le pharmacien(ne) risque de le mentionner et ceci pourrait créer dans doute dans le plan de traitement.

Expert 6: Reponse: Renforcée Justification: C'est le traitement de choix de la crise migraineuse, les ISRS ne sont pas une contre indication et les crises non soulagées sont sources de préoccupations, ont un impact sur la dépression tout comme transiger avec l'employeur et l'incompréhension d'un absentéisme.

Learner's Response:
Reponse: Inchangée 
Justification: Le premier choix serait d’opter plutôt pour un AINS. Cependant, les triptans ne sont pas contre indiqués. Le risque de syndrome serotoninergique est très faible.
</Scenario 2>

<Scenario 3>
Scenario 3:

Si vous pensiez à ... 3- Débuter Sumatriptan 50 mg PO

Et qu’alors ... La patiente vous dit qu’elle a déjà tenté le Zolmitriptan dans le passé qui n’avait pas été efficace.

Experts' Responses:


Expert 2: Reponse: Affaiblie Justification: La non-réponse à un triptan spécifique ne veut pas dire qu'elle ne répondra pas à un autre triptan, bien que la chance est moindre. En comparant les triptan entre eux, des études ont démontré une légère supériorité de l'Élétriptan, donc je le considérerais légèrement plus qu'un autre dans ce cas précis, mais ce n'est qu'une très légère préférence. Par contre, je mettrais l'accent sur l'utilisation TÔT d'un triptan et sur un AINS et/ou Acetaminophen concomitants pour maximiser efficacité.

Expert 3: Reponse: Affaiblie Justification: Échec à un triptan n'égale pas nécessairement échec aux autres revoir aussi avec elle pourquoi le Zolmi n'avait pas été efficace j'aurais tendance à débuter Suma 100.

Expert 4: Reponse: Affaiblie Justification: J’irais avec le 100 mg d’emblée.

Expert 5: Reponse: Affaiblie Justification: Même si un triptan n'est pas efficace un autre triptan devrait quand même être essayé. Je vérifierai si migraine à début rapide. Zolmitriptan et Sumatriptan per os ont Tmax un peu plus long que Almotriptan, Rizatriptan, Eletriptan, et Sumatriptan IN ou SC. En principe, si un triptan n'aide pas, mais bien toléré, je recommande un autre. Utiliser caractéristiques de la migraine peut aider dans le choix (migraine au réveil, migraine menstruelle, nausée/vomissement précoce, pic de douleur rapide = < 60 min).

Expert 6: Reponse: Inchangée Justification: La réponse thérapeutique peut varier d’un triptan à l’autre. Ça vaut la peine d’essayer un autre. Aussi, il est important de revoir comment le triptan est utilisé avant de conclure à un échec thérapeutique. Aussi, un AINS pourrait être tenté également.

Learner's Response:
Reponse: Affaiblie Justification: Il faudrait déterminer si le Z est ns ou pos, à 2.5 mg per os pas tj optimal. La dose de suma 50 est nettement insuffisante pour traiter une crise suffisamment sévère pour être non fonctionnel.
</Scenario 3>
</Situation 1>


<Situation 2>
Situation 2: Vous voyez en clinique externe une patiente connue pour migraines épisodiques. Elle fait en moyenne trois à quatre crises de migraines par mois. Elle doit s’absenter du travail lorsqu’elle a une crise. Elle a déjà pris par le passé le Zolmitriptan et le Rizatriptan qui étaient peu efficace. Elle n’a pas d’antécédents familiaux pertinents et ne prend pas de médicaments sur une base régulière.

<Scenario 4>
Scenario 4:

Si vous pensiez à ... 1- Débuter un nouveau triptan

Et qu’alors ... La patiente vous informe qu’elle a tendance à attendre que la céphalée forte avant de prendre ses médicaments

Experts' Responses:


Expert 2: Reponse: Affaiblie Justification: L'efficacité est nettement plus importante lorsque le triptan est pris au début de la crise alors que la céphalée est d'intensité légère. Je retenterai un triptan connu d'autant plus qu'il n'est pas mentionné d'effet secondaire.

Expert 3: Reponse: Inchangée Justification: Encore ici, l'éducation du timing de la prise de médicament (à prendre tôt) est la plus importante. Aussi, si la patiente a nausées ++ ou vomissement ceci serait à évaluer sur sa tolérance à prendre médicament PO et pourrait être la cause du délai. Encore ici, légère préférence pour Eletriptan, mais retenter le Zolmi ou Risatriptan avec meilleur timing (surtout si elle en a encore à la maison) serait une autre option.

Expert 4: Reponse: Affaiblie Justification: Il est important de prendre le triptan dans les deux heures après le début des symptômes. Sinon, il ne sera pas efficace.

Expert 5: Reponse: Affaiblie Justification: D'abord retenter l'un ou l'autre des 2 triptans, mais le plus tôt possible en début de crise avant de songer à débuter un 3e.

Expert 6: Reponse: Affaiblie Justification: Elle devrait d’abord essayer de les prendre plus tôt si pas effet secondaire.

Learner's Response:
Reponse: Fortement affaiblie Justification: Si Zolmitriptan et Rizatriptan bien toléré je les reprendrai, mais avec conseil de prendre le traitement le plus tôt possible après début des symptômes de migraine et répéter la dose 2h plus tard si migraine persiste.
</Scenario 4>

<Scenario 5>
Scenario 5:

Si vous pensiez à ... 2- Débuter Sumatriptan 50 mg PO

Et qu’alors ... La patiente vous dit qu’elle a beaucoup de nausée qui accompagne ses migraines.

Experts' Responses:

Expert 2: Reponse: Affaiblie Justification: Un triptan par voie intranasale pourrait être plus efficace et mieux toléré chez un patient avec nausée lors de ses migraines. Une gastro parésie peut être associée aux nausées et réduire la rapidité d’absorption du médicament oral.

Expert 3: Reponse: Inchangée Justification: J’ajouterais anti nauséeux comme metoclopramide , mais si elle vomit alors j’irais vers un spray nasal ou injection.

Expert 4: Reponse: Fortement affaiblie Justification: Vu nausée importante j'opterai pour formulation sc (suma), intranasale (zolmi, suma) ou un cachet fondant (zolmi, riza).

Expert 5: Reponse: Affaiblie Justification: Sumatriptan SQ pourrait être meilleure option. Sumatriptan IN pourrait aussi être option, car si vomissement dose ne serait pas "perdue", mais certains patient ont augmentation des nausées avec médication IN. Si Rizatriptan ne fonctionne que 50% du temps, je pense que la "basse" dose de Sumatriptan 50 mg a moins de chance de fonctionner que 100 mg, alors je dirais d'emblée à la patiente que si 50 mg ne fonctionne pas bien, de rapidement tenter une prochaine fois 100 mg d'emblée.

Expert 6: Reponse: Affaiblie Justification: Songer à une voie d'administration IN ou SC.

Learner's Response:
Reponse: Fortement affaiblie Justification: Suma 50 mg dose trop faible. Je tenterai une combinaison de son Riza avec un anti-inflammatoire avec ou sans antinauséeux (metoclop) en m'assurant que la médication est prise au début. Je donnerai aussi l'option d'un traitement nasal avec Zolmi 5 mg, en sauvetage après 2h éventuellement suma sc.
</Scenario 5>

<Scenario 6>
Scenario 6:

Si vous pensiez à ... 3- Suggérer de débuter un Sumatriptan à prendre en combinaison avec un AINS

Et qu’alors ... La patiente vous dit que depuis deux mois, sa fréquence de crises de migraine a augmenté à six par mois avec des céphalées résiduelles entre ses crises pendant 24-48h.

Experts' Responses:


Expert 2: Reponse: Inchangée Justification: L’ajout d’un AINS peut améliorer l’effet du triptan. Par contre, la patiente semble être en train de développer des migraines chroniques et un traitement préventif pourrait aider à réduire la fréquence des symptômes et améliorer la réponse au traitement aigu.

Expert 3: Reponse: Renforcée Justification: Un traitement insuffisant ou peu efficace des migraines pourrait être une cause de sensibilisation et d'augmentation de la fréquence, donc essayer un traitement plus "agressif" tel que Triptan et AINS combiné est très approprié. Évidemment, voir habitudes de vie, facteurs stress, etc., et pertinence de considérer traitement prophylactique.

Expert 4: Reponse: Fortement renforcée Justification: Le traitement de crise ne semble pas adéquat donc de renforce l'idée d'un traitement combiné, mais je considérai également un traitement préventif chez cette patiente. Sa maladie semble progresser.

Expert 5: Reponse: Renforcée Justification: Faudra fortement envisager une prophylaxie en plus d'optimiser le traitement aigu avec le combo triptan/AINS.

Expert 6: Reponse: Inchangée Justification: L’AINS en combinaison va peut-être mieux casser ses migraines et donc avoir moins de céphalées résiduelles. Mais il faudra un préventif aussi et surveiller de près la survenue de C.O.M.

Learner's Response:
Reponse: Affaiblie Justification: Voir commentaires question précédente. Je réviserais les habitudes de vie et les déclencheurs, viserais un soulagement complet des crises et envisagerais un traitement préventif.
</Scenario 6>
</Situation 2>
"""


training_3 = """
Now analyze the learner's responses to the following training. 

Training Objectives:
- Différencier les types de céphalées
- Poser un diagnostic pertinent en contexte clinique complexe par la discrimination des caractéristiques cliniques de la migraine, des céphalées de tension et des céphalées médicamenteuses
- Évaluer de façon critique les options thérapeutiques aiguës, préventives et hormonales dans la prise en charge des migraines

Trainings Content:

Module 3 : Traitement préventif de la migraine

<Situation 1>
Situation 1: Vous voyez en clinique externe une patiente connue pour migraines. Ses crises sont d’intensité modérées à sévères et elle doit s’absenter du travail parfois lors de celles-ci. Elle prend de manière adéquate un AINS et un triptan lors de ses crises. Elle n’a pas d’antécédents familiaux pertinents et ne prend pas de médicaments sur une base régulière.

<Scenario 1>
Scenario 1:

Si vous pensiez à ... Débuter Amitriptyline 25mg HS

Et qu’alors ... La patiente vous indique qu’elle fait 8 à 10 crises par mois et que le Sumatriptan est toujours efficace.

Experts' Responses:


Expert 2: Reponse: Inchangée Justification: Je débuterais avec une dose plus petite, les effets secondaires à 25 mg sont pratiquement garants d'un échec de ce préventif et ensuite d'une méfiance de la part des patients face aux préventifs. Je réviserais aussi les comorbidités pour déterminer si ce préventif oral est adéquat pour cette patiente, un autre pourrait être plus adapté.

Expert 3: Reponse: Renforcée Justification: D'abord 10 mg.

Expert 4: Reponse: Fortement renforcée Justification: La fréquence est quand même élevée et même si elle dit le sum afficace, elle doit parfois s’absenter du travail.

Expert 5: Reponse: Inchangée Justification: Besoin de discuter avec la patiente des avantages et inconvénients de Tx préventif, mais elle a un absentéisme au travail malgré prise de Sumatriptan. Donc je ne la considérerais pas "contrôlée" et le risque de ne pas traiter serait une possible augmentation de la fréquence des migraines vers une chronicisation.

Expert 6: Reponse: Inchangée Justification: En lien le nouveau langage qu'on essaye de mettre en place, peut-être enlever le "s" à migraine dans la première phrase. Même si sumatriptan fonctionne elle doit quand même parfois manque le travail donc l'impact fonctionnel justifie le début d'un traitement préventif. Raison pourquoi on débute à 25 mg? Je commence habituellement à 5-10 mg hs pour m'assurer d'une bonne tolérabilité en premier et parfois les patients ont des bonnes réponses malgré une dose plus petite.

Learner's Response:
Reponse: Affaiblie Justification: La fréquence des migraines n’est pas assez importante pour justifier la prise d’un traitement préventif. De plus, elle répond à son traitement de crise.
</Scenario 1>

<Scenario 2>
Scenario 2:

Scenario 2:

Si vous pensiez à ... Débuter propranolol 60 mg die

Et qu’alors ... La patiente vous indique qu’elle fait 8 crises par mois non-soulagée par ses traitements aigus. Elle désire avoir une grossesse dans la prochaine année.

Experts' Responses:


Expert 2: Reponse: Inchangée Justification: Je débuterais avec une dose plus faible pour augmenter graduellement à cette dose. Le propranolol est compatible avec une grossesse.

Expert 3: Reponse: Fortement renforcée Justification: Propanolol un des prophylactiques à privilégier en grossesse et un des prophylactiques de première ligne.

Expert 4: Reponse: Inchangée Justification: Discuter de l'indication de stabiliser ses migraines dans un premier temps, quitte à cesser le propranolol en cas de grossesse en sachant que celle-ci pourra entraîner une réduction de la fréquence des crises.

Expert 5: Reponse: Fortement renforcée Justification: Elle a besoin d’un préventif, car incapacité et haute fréquence , mais on lui suggérera de sevrer le propranolol au moment où elle fera ses démarches de grossesse. Et si elle tombe enceinte sous propra, pas inquiétude sur teratogenecité.

Expert 6: Reponse: Inchangée Justification: Traitement préventif indiqué vu 8 crises par mois, en plus de ne pas avoir trouvé un traitement de crise efficace ainsi que l'impact fonctionnel avec manque de travail. Propranolol option adéquate pendant la grossesse.

Learner's Response:
Reponse: Affaiblie 
Justification: Avant de débuter un traitement préventif, surtout considérant la grossesse possible dans ,a prochaine année, il serait préférable de trouver un traitement aigu efficace.
</Scenario 2>

<Scenario 3>
Scenario 3:

Si vous pensiez à ... Débuter topiramate 50 mg HS

Et qu’alors ... La patiente vous indique qu’elle est avocate et elle redoute les effets secondaires des traitements.

Experts' Responses:


Expert 2: Reponse: Affaiblie Justification: Encore une fois dose initiale trop élevée, de plus les effets cognitifs de ce médicament pourraient interférer avec le travail de cette patiente. J'éviterais ce médicament pour cette patiente à moins qu'elle n'en ait tenté d'autres qui auraient été non efficaces, alors je débuterai à 12.5, en l'avertissant clairement. Parfois les patients le tolèrent.

Expert 3: Reponse: Fortement affaiblie Justification: Opter pour une alternative.

Expert 4: Reponse: Affaiblie Justification: Considérant les effets secondaires possibles du topiramate au niveau cognitif et au niveau du langage, une autre option devrait être considérée (propanolol).

Expert 5: Reponse: Fortement affaiblie Justification: J'opterais dans ce cas pour un bêta bloqueur ou autre antihypertenseur (candesartan) ou antidépresseur tricyclique si absence de contre-indication. Si migraine épisodique à base fréquence considérer approche avec Vitamine B2, Mg et reparler gestion habitudes de vie. Si échecs autres classes, commence petites doses de TPX 12.5 mg hs et augmenter très progressivement, en bonifiant la dose hs en premier et ensuite introduire une dose le matin, selon tolérance et efficacité tout en rassurant la pte qu'elle pourrait arrêter à tout moment si non-toléré elle qu'elle n'aura pas a craindre des effets secondaires permanents.

Expert 6: Reponse: Affaiblie Justification: Ça dépend de ce qu’elle a déjà essayé comme autres préventifs .On lui expliquera les risques de troubles de concentration , elle pourra le débuter très progressivement, diminuant ce risque. Mais ce n’est pas le premier choix.

Learner's Response:
Reponse: Fortement affaiblie 
Justification: Topiramate peut avoir effets cognitifs importants, bien que la prise qHS seulement parfois puisse les minimiser. Je débuterais un autre médicament (ex: Vit B6, Magnésium, possible un antidépresseur tricyclique tel Nortriptyline ou même Désipramine, car moins d'effet secondaire vs amitriptyline), ou sinon une plus petite dose avec augmentation lente: ex: 12.5 mg qHS pour plusieurs semaines).
</Scenario 3>
</Situation 1>

<Situation 2>
Situation 2: Vous voyez en clinique externe une patiente connue pour migraines. Ses crises sont d’intensité modérées à sévères et elle doit s’absenter du travail parfois lors de celles-ci. Elle prend de manière adéquate un AINS et un triptan lors de ses crises. Elle a déjà tenté le propranolol, l’amitriptyline et le topiramate qui n’étaient pas efficaces ou qu’elle n’a pas toléré. Elle n’a pas d’antécédents familiaux pertinents et ne prend pas de médicaments sur une base régulière.

<Scenario 4>
Scenario 4:

Si vous pensiez à ... Débuter Érénumab

Et qu’alors ... La patiente vous indique qu’elle désire une grossesse dans la prochaine année

Experts' Responses:


Expert 2: Reponse: Affaiblie Justification: La fréquence des migraines justifie la prise d’un traitement préventif, mais les anti CGRP ne sont pas recommandés en grossesse.

Expert 3: Reponse: Inchangée Justification: Étant donné la fréquence élevée et l'impact habituel de cette fréquence élevée de migraine, j'avertirai la patiente qu'il doit y avoir un écart de 4-5 mois entre le début de la grossesse et la dernière dose d'erenumab. Je me mettrai d'accord avec elle sinon je ne le prescrirai pas.

Expert 4: Reponse: Fortement affaiblie Justification: Il faut cesser erenumab au moins 5 mois avant grossesse. Effets sur grossesse inconnus, et reste ad 5 mois dans le corps après arrêt. Suggérerons BOTOX, qui sera maintenu jusqu’à grossesse, puis cessé.

Expert 5: Reponse: Affaiblie Justification: Pas encore assez de données pour pouvoir considérer les MAb en prévention migraine durant la grossesse. Dans ce cas, je privilégierais de considérer Botox même si encore là pas officiellement accepté en grossesse.

Expert 6: Reponse: Affaiblie Justification: Je n'ai pas répondu fortement affaiblie parce que vu que les MABs agissent relativement rapidement on pourrait l'offrir un MAB pour 6 mois ce qui pourrait stabiliser la maladie rapidement et ensuite cesser MAB (au moins 5 mois avant grossesse) et opter pour le Botox (off label). Vu aucune recommandation officielle en grossesse, mais 30 ans d'utilisation pour multiples indications suggérant une sécurité relative en grossesse pour la migraine chronique réfractaire aux traitements per os standards.

Learner's Response:
Reponse: Fortement affaiblie 
Justification: Pas assez de données disponibles
</Scenario 4>

<Scenario 5>
Scenario 5:

Si vous pensiez à ... 5- Référer pour des injections de Botox

Et qu’alors ... La patiente vous indique qu’elle a huit crises par mois en moyenne, sans céphalées entre les épisodes.

Experts' Responses:


Expert 2: Reponse: Affaiblie Justification: Actuellement, les critères diagnostiques de migraine chronique ne sont pas rencontrés et les injections de toxine botulinique ne sont recommandées qu’en migraine chronique.

Expert 3: Reponse: Renforcée Justification: La fréquence des migraines justifie la prise d’un traitement préventif et, globalement, les anti-CGRP sont bien tolérés.

Expert 4: Reponse: Fortement renforcée Justification: Excellente tolérabilité de ce Rx en général.

Expert 5: Reponse: Renforcée Justification: Les MAb sont en général bien tolérés excepté constipation et effets locaux. Un MAb est probablement une des options avec le moins d'effet secondaire, quoique l'Onabotulotoxine (Botox) serait aussi très approprié ici.

Expert 6: Reponse: Fortement renforcée Justification: MABs bon choix et bien toléré en général donc bonne option à mon avis.

Learner's Response:
Reponse: Fortement affaiblie 
Justification: Elle ne remplit pas les critères de remboursement pour l'utilisation du Botox, la fréquence des céphalées devant être de 15 jours et plus par mois avec 8 épisodes et plus remplissant les critères de migraine ou soulagé par un médicament abortif spécifique au traitement de la migraine. Toutefois je ne pense pas que l'utilisation du Botox soit totalement inadéquate.
</Scenario 5>

<Scenario 6>
Scenario 6:

Si vous pensiez à ... 3- Référer pour des injections de Botox

Et qu’alors ... La patiente vous indique qu’elle a huit crises par mois en moyenne, sans céphalées entre les épisodes.

Experts' Responses:


Expert 2: Reponse: Affaiblie Justification: Actuellement, les critères diagnostiques de migraine chronique ne sont pas rencontrés et les injections de toxine botulinique ne sont recommandées qu’en migraine chronique.

Expert 3: Reponse: Fortement affaiblie Justification: Pas d'efficacité démontrée en migraine épisodique fréquente comme c'est le cas dans cette situation.

Expert 4: Reponse: Affaiblie Justification: En théorie, cette patiente ne rencontre pas les critères stricts de migraine chronique (plutôt migraine épisodique à haute fréquence), donc ne serait pas éligible au Botox, ce qui pourrait causer rejet pas assurances. Toutefois, le Botox reste à mon avis une option à considérer, même si un MAb était mieux accepté par assureur et en théorie tout aussi efficace.

Expert 5: Reponse: Fortement affaiblie Justification: BOTOX pas indiqué en migraine épisodique , même si haute fréquence.

Expert 6: Reponse: Fortement affaiblie Justification: Botox seulement recommandé pour la migraine chronique (15 jours ou plus de céphalées par mois dont 8 jours de migraines) donc cette patiente ne qualifie pas pour ce traitement.

Learner's Response:
Reponse: Fortement affaiblie 
Justification: Elle ne remplit pas les critères de remboursement pour l'utilisation du Botox, la fréquence des céphalées devant être de 15 jours et plus par mois avec 8 épisodes et plus remplissant les critères de migraine ou soulagé par un médicament abortif spécifique au traitement de la migraine. Toutefois je ne pense pas que l'utilisation du Botox soit totalement inadéquate.
</Scenario 6>
</Situation 2>
"""


training_objectives = """
Training Objectives:
- Différencier les types de céphalées
- Poser un diagnostic pertinent en contexte clinique complexe par la discrimination des caractéristiques cliniques de la migraine, des céphalées de tension et des céphalées médicamenteuses
- Évaluer de façon critique les options thérapeutiques aiguës, préventives et hormonales dans la prise en charge des migraines
"""