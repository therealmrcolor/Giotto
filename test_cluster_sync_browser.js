// Test diretto della sincronizzazione cluster
// Copia e incolla questo nella console del browser per testare

console.log('=== TEST SINCRONIZZAZIONE CLUSTER ===');

// Simula la chiamata API per ottenere i colori
fetch('/api/cabin/1/colors')
  .then(response => response.json())
  .then(data => {
    console.log('Dati colori ricevuti:', data);
    
    const colors = data.colors || [];
    console.log('Numero colori:', colors.length);
    
    // Estrai cluster unici
    const clustersFromColors = [...new Set(colors.map(c => c.cluster).filter(c => c))];
    console.log('Cluster dai colori:', clustersFromColors);
    
    // Ottieni ordine cluster attuale
    return fetch('/api/cabin/1/cluster_order');
  })
  .then(response => response.json())
  .then(clusterData => {
    console.log('Ordine cluster attuale:', clusterData.order);
    
    // Qui dovresti vedere se i cluster sono allineati
    console.log('=== FINE TEST ===');
  })
  .catch(error => {
    console.error('Errore nel test:', error);
  });
