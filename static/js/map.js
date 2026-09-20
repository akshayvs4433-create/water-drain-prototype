const defaultPosition = { lat: 12.9716, lng: 77.5946 };

function addMarker(map, report) {
  const x = ((report.longitude - (defaultPosition.lng - 0.55)) / 1.1) * 100;
  const y = (1 - (report.latitude - (defaultPosition.lat - 0.45)) / 0.9) * 100;
  const marker = document.createElement('button');
  marker.type = 'button';
  marker.className = `public-marker ${report.status === 'In Progress' ? 'in-progress' : 'unresolved'}`;
  marker.style.left = `${Math.max(2, Math.min(98, x))}%`;
  marker.style.top = `${Math.max(2, Math.min(98, y))}%`;
  marker.title = report.ticket_id;
  marker.setAttribute('aria-label', `View ${report.ticket_id}`);
  marker.addEventListener('click', () => {
    const previous = map.querySelector('.public-map-popup');
    if (previous) previous.remove();
    const popup = document.createElement('div');
    popup.className = 'public-map-popup';
    popup.innerHTML = `<strong>${report.ticket_id}</strong><br>${report.description}<br>${report.ward}<br>${report.status}<br>${report.created_at}`;
    map.appendChild(popup);
  });
  map.appendChild(marker);
}

function initPublicMap() {
  const reports = window.REPORT_DATA || [];
  const map = document.getElementById('reports-map');
  map.classList.add('prototype-map');
  map.querySelector('.map-message').textContent = reports.length ? 'Click a marker to view report details' : 'No open report locations yet';
  reports.forEach((report) => addMarker(map, report));
}

document.addEventListener('DOMContentLoaded', initPublicMap);
