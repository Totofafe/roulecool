/**
 * RouleCool — Seuils de confort
 * ──────────────────────────────
 * Modifier uniquement ce fichier pour recalibrer l'échelle.
 * Ces valeurs sont utilisées par index.html et widget.html.
 *
 * Après modification :
 *   1. Mettre à jour SEUILS dans analyse_trajet.py (même valeurs)
 *   2. Vider la table Grist et ré-importer les trajets existants
 *   3. git add seuils.js && git commit -m "recalibrage seuils" && git push
 */

const SEUILS = {
  confortable: 5.0,   // vibration < 5.0  → Confortable (vert foncé)
  acceptable:  8.5,   // vibration < 8.5  → Acceptable  (vert clair)
                      // vibration >= 8.5 → Inconfortable (rouge)

  labels: {
    confortable:  'Confortable',
    acceptable:   'Acceptable',
    inconfortable: 'Inconfortable',
  },

  couleurs: {
    confortable:  '#2E7D32',  // vert foncé
    acceptable:   '#A5D6A7',  // vert clair
    inconfortable: '#F44336', // rouge
  }
};

function getScore(vibration) {
  if (vibration < SEUILS.confortable) return SEUILS.labels.confortable;
  if (vibration < SEUILS.acceptable)  return SEUILS.labels.acceptable;
  return SEUILS.labels.inconfortable;
}

function getColor(score) {
  if (score === SEUILS.labels.confortable)  return SEUILS.couleurs.confortable;
  if (score === SEUILS.labels.acceptable)   return SEUILS.couleurs.acceptable;
  return SEUILS.couleurs.inconfortable;
}

function getLegendText() {
  return {
    confortable:  `&lt; ${SEUILS.confortable} m/s²`,
    acceptable:   `${SEUILS.confortable} \u2013 ${SEUILS.acceptable} m/s²`,
    inconfortable: `&gt; ${SEUILS.acceptable} m/s²`,
  };
}
