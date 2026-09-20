const defaultPosition = { lat: 12.9716, lng: 77.5946 };

function updateWard(latitude, longitude) {
  fetch(`/api/wards?lat=${latitude}&lng=${longitude}`)
    .then((response) => response.json())
    .then((data) => { document.getElementById('ward-display').textContent = data.ward || 'Prototype Review Zone'; })
    .catch(() => { document.getElementById('ward-display').textContent = 'Prototype Review Zone'; });
}

function setLocation(latitude, longitude) {
  document.getElementById('latitude').value = latitude;
  document.getElementById('longitude').value = longitude;
  document.getElementById('coordinate-readout').textContent = `${latitude.toFixed(5)}, ${longitude.toFixed(5)}`;
  updateWard(latitude, longitude);
}

function initLocationPicker() {
  const mapArea = document.getElementById('report-map');
  mapArea.classList.add('prototype-map');
  mapArea.querySelector('.map-message').textContent = 'Click anywhere to place the report pin';
  mapArea.addEventListener('click', (event) => {
    const bounds = mapArea.getBoundingClientRect();
    const x = Math.max(0, Math.min(bounds.width, event.clientX - bounds.left));
    const y = Math.max(0, Math.min(bounds.height, event.clientY - bounds.top));
    const latitude = defaultPosition.lat + (0.45 - (y / bounds.height) * 0.9);
    const longitude = defaultPosition.lng + ((x / bounds.width) - 0.5) * 1.1;
    const previousPin = mapArea.querySelector('.prototype-pin');
    if (previousPin) previousPin.remove();
    const pin = document.createElement('span');
    pin.className = 'prototype-pin';
    pin.textContent = '●';
    pin.style.left = `${x}px`;
    pin.style.top = `${y}px`;
    mapArea.appendChild(pin);
    setLocation(latitude, longitude);
  });
}

document.addEventListener('DOMContentLoaded', () => {
  initLocationPicker();
  document.getElementById('locate-btn').addEventListener('click', () => {
    if (!navigator.geolocation) return alert('Geolocation is not available in this browser.');
    navigator.geolocation.getCurrentPosition(
      (position) => setLocation(position.coords.latitude, position.coords.longitude),
      () => alert('Location permission was denied. You can select a point directly on the map.'),
      { enableHighAccuracy: true, timeout: 10000 }
    );
  });
});
