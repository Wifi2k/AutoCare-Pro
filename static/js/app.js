const refreshButton = document.querySelector('#refreshBtn');
const vehicleList = document.querySelector('#vehicleList');

function renderVehicles(vehicles) {
  if (!vehicleList) return;
  if (!vehicles.length) {
    vehicleList.innerHTML = '<div class="empty">No vehicles added yet. Use the form to create the first record.</div>';
    return;
  }
  vehicleList.innerHTML = vehicles.map(vehicle => `
    <article class="vehicle-card">
      <h3>${vehicle.year} ${vehicle.make} ${vehicle.model}</h3>
      <p><strong>Mileage:</strong> ${Number(vehicle.mileage).toLocaleString()} miles</p>
      ${vehicle.notes ? `<p><strong>Notes:</strong> ${vehicle.notes}</p>` : ''}
    </article>
  `).join('');
}

async function refreshVehicles() {
  const response = await fetch('/api/vehicles');
  const vehicles = await response.json();
  renderVehicles(vehicles);
}

if (refreshButton) {
  refreshButton.addEventListener('click', refreshVehicles);
}
