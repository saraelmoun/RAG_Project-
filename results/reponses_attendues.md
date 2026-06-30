# Réponses attendues — jeu de référence (gold set)

Ce fichier est la **vérité terrain** pour évaluer la récupération (retrieval) et la
génération du RAG. Chaque réponse provient **exclusivement** des documents de `corpus/`.
Un modèle sans accès aux documents ne peut pas inventer ces valeurs : c'est volontaire.

Format : question-piège → réponse exacte attendue → document source.

---

## Document 1 — `corpus/teletravail.md` (réf. TR-2024/Acme)

1. **Combien de jours de télétravail par semaine sont autorisés sur le site de
   Castelnau-le-Vieux ?**
   → **2,5 jours par semaine** (et non 3,5 j comme à Roubaix-Épône).
   *Source : §1.*

2. **Quel formulaire faut-il déposer pour demander du télétravail, et sur quel portail ?**
   → Formulaire **WF-17**, sur le portail interne **« Hélios »**.
   *Source : en-tête + §2.*

3. **De combien de temps dispose Mme Brandroux pour valider une demande, et que se
   passe-t-il ensuite ?**
   → **72 heures** ; passé ce délai, la demande est **automatiquement transférée au
   responsable de site**.
   *Source : §2.*

4. **Quelle est l'indemnité mensuelle pour un « télétravailleur renforcé » ?**
   → **26,90 € par mois** (contre 18,40 € pour le forfait standard).
   *Source : §3.*

---

## Document 2 — `corpus/conges.md` (réf. CG-2023/Acme-bis)

1. **Combien de jours de congés « ancienneté » sont accordés, et à partir de quand ?**
   → **6,5 jours**, dès **3 ans révolus** dans l'entreprise (puis +1 jour tous les 4 ans,
   plafond 11 jours).
   *Source : §1.*

2. **Quel est le préavis pour poser un congé de moins de 5 jours ?**
   → **6 jours ouvrés** (contre 21 jours calendaires pour un congé de 5 jours ou plus).
   *Source : §3 « Délais de pose ».*

3. **Quel est le code d'absence de la journée de bénévolat solidaire, et quelle liste
   d'associations fait foi ?**
   → Code **BS-08** ; liste des partenaires **PL-2024**.
   *Source : §3 « Congés exceptionnels ».*

4. **Jusqu'à quelle date peut-on reporter ses congés non pris, et dans quelle limite ?**
   → Jusqu'au **31 mai** de l'année suivante, dans la limite de **9 jours** (report
   intégral 24 mois pour le statut EXP-5).
   *Source : §4.*

---

## Document 3 — `corpus/notes_de_frais.md` (réf. NF-2024/Acme)

1. **Quel est le plafond d'un dîner en déplacement en France métropolitaine ?**
   → **31,50 € par repas** (le déjeuner est à 19,80 €).
   *Source : §1.*

2. **Quel est le taux d'indemnité kilométrique, et que devient-il au-delà de
   4 200 km/an ?**
   → **0,427 € / km**, puis **0,318 € / km** au-delà de 4 200 km/an.
   *Source : §2.*

3. **Quel abattement s'applique à une note de frais saisie en retard, et à partir de
   quand est-elle rejetée automatiquement ?**
   → Abattement de **40 %** au-delà de 30 jours ; **rejet automatique au-delà de
   45 jours** (référence de rejet **RJ-12**).
   *Source : §4.*

4. **Quel est le plafond de repas sur le site de Quezáltepec (Guatemala) ?**
   → **44,00 € par repas** (justificatif obligatoire au-delà de 12,00 €).
   *Source : §1.*

---

## Notes d'usage

- Total : **3 documents × 4 questions = 12 paires question/réponse.**
- Ces questions servent à deux choses : (1) vérifier que le **retrieval** ramène bien le
  bon chunk, (2) vérifier que la **génération** restitue la valeur exacte sans
  l'inventer.
- Piège volontaire : plusieurs faits ont une variante « par défaut » qu'un LLM
  devinerait (ex. 2 jours de télétravail, barème fiscal 0,4 €/km). Toute réponse qui
  retombe sur la valeur générique au lieu de la valeur Acme = **hallucination détectée**.
