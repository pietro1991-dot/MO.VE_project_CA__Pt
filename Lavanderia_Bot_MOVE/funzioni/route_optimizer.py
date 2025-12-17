"""
Route Optimizer - Genera percorso ottimizzato con Google Maps Directions API
Crea URL navigabile e calcola ordine ottimale visite giornaliere
"""

import os
import json
import requests
from datetime import datetime
from typing import List, Dict, Tuple

class RouteOptimizer:
    """
    Ottimizza percorso giornaliero usando Google Maps Directions API
    Free tier: 40,000 richieste/mese (~1,300/giorno)
    """
    
    def __init__(self, api_key=None):
        """
        Inizializza optimizer con Google Maps API key
        
        Args:
            api_key: Chiave API Google Maps (opzionale, cerca in Config/google_maps_api_key.txt)
        """
        if api_key:
            self.api_key = api_key
        else:
            # Cerca API key in Config/ (parent di funzioni/)
            script_dir = os.path.dirname(os.path.abspath(__file__))
            root_dir = os.path.dirname(script_dir)
            config_dir = os.path.join(root_dir, 'Config')
            api_key_file = os.path.join(config_dir, 'google_maps_api_key.txt')
            
            if os.path.exists(api_key_file):
                with open(api_key_file, 'r', encoding='utf-8') as f:
                    self.api_key = f.read().strip()
                print(f"[OK] Google Maps API key caricata")
            else:
                print(f"[WARN] Google Maps API key non trovata: {api_key_file}")
                print(f"[INFO] Crea file Config/google_maps_api_key.txt con la tua API key")
                self.api_key = None
        
        self.base_url = "https://maps.googleapis.com/maps/api/directions/json"
    
    def _normalize_address(self, address: str) -> str:
        """
        Normalizza indirizzo aggiungendo città se mancante per evitare ambiguità
        
        Args:
            address: Indirizzo da normalizzare
            
        Returns:
            Indirizzo completo con città
        """
        address = address.strip()
        
        # Se l'indirizzo non contiene già "Modena" o un CAP di Modena (411xx), aggiungilo
        if 'modena' not in address.lower() and not any(cap in address for cap in ['41121', '41122', '41123', '41124', '41125', '41126']):
            # Aggiungi ", Modena (MO)" alla fine
            address = f"{address}, Modena (MO)"
            print(f"[INFO] Indirizzo normalizzato: {address}")
        
        return address
    
    def optimize_route(self, addresses: List[str], start_location: str = None, end_location: str = None) -> Dict:
        """
        Ottimizza percorso visitando tutti gli indirizzi
        
        Args:
            addresses: Lista indirizzi da visitare
            start_location: Punto partenza (default: Magazzino Buon Pastore)
            end_location: Punto arrivo (default: stesso di partenza)
        
        Returns:
            {
                'optimized_order': [indici ordinati],
                'route_url': 'URL Google Maps navigabile',
                'total_distance': distanza_km,
                'total_duration': durata_minuti,
                'waypoints': [indirizzi ordinati],
                'success': bool
            }
        """
        if not self.api_key:
            print("[ERROR] API key non disponibile - impossibile ottimizzare route")
            return self._fallback_order(addresses)
        
        if not addresses or len(addresses) == 0:
            return {
                'success': False,
                'error': 'Nessun indirizzo fornito',
                'optimized_order': [],
                'route_url': '',
                'waypoints': []
            }
        
        # Normalizza tutti gli indirizzi
        addresses = [self._normalize_address(addr) for addr in addresses]
        
        # MAGAZZINO CENTRALE: punto partenza e arrivo
        if not start_location:
            start_location = "Via Buon Pastore 52, 41125 Modena (MO)"
        
        if not end_location:
            end_location = start_location  # Ritorno al magazzino
        
        # Se solo 1-2 indirizzi, non serve ottimizzazione
        if len(addresses) <= 2:
            return self._simple_route(addresses, start_location, end_location)
        
        # Tutti gli indirizzi sono waypoints (partenza e arrivo fissi al magazzino)
        waypoints = addresses
        
        print(f"[ROUTE] Ottimizzazione percorso per {len(addresses)} indirizzi...")
        print(f"[ROUTE] Partenza: {start_location}")
        print(f"[ROUTE] Arrivo: {end_location}")
        
        try:
            # Chiamata API Google Maps Directions con waypoint optimization
            # Partenza = Magazzino, Destinazione = Magazzino, Waypoints = appartamenti
            params = {
                'origin': start_location,
                'destination': end_location,
                'waypoints': 'optimize:true|' + '|'.join(waypoints),
                'mode': 'driving',
                'language': 'it',
                'key': self.api_key
            }
            
            response = requests.get(self.base_url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if data['status'] != 'OK':
                print(f"[ERROR] Google Maps API error: {data['status']}")
                if 'error_message' in data:
                    print(f"[ERROR] Messaggio: {data['error_message']}")
                return self._fallback_order(addresses)
            
            # Estrai ordine ottimizzato waypoints
            waypoint_order = data['routes'][0].get('waypoint_order', [])
            
            # Ordine ottimizzato: gli indici si riferiscono ai waypoints originali
            optimized_indices = waypoint_order
            optimized_addresses = [addresses[i] for i in waypoint_order]
            
            # Calcola distanza e durata totali
            total_distance = 0  # metri
            total_duration = 0  # secondi
            
            for leg in data['routes'][0]['legs']:
                total_distance += leg['distance']['value']
                total_duration += leg['duration']['value']
            
            # Genera URL navigabile (Google Maps app) - usa gli indirizzi ottimizzati
            # NON includere ritorno perché già gestito da start_location = end_location
            route_url = self._generate_maps_url(optimized_addresses, include_return=False)
            
            print(f"[ROUTE] Ottimizzazione completata:")
            print(f"  - Distanza totale: {total_distance / 1000:.2f} km")
            print(f"  - Durata stimata: {total_duration / 60:.0f} minuti")
            print(f"  - Ordine ottimizzato: {optimized_indices}")
            
            return {
                'success': True,
                'optimized_order': optimized_indices,
                'route_url': route_url,
                'total_distance_km': round(total_distance / 1000, 2),
                'total_duration_minutes': round(total_duration / 60),
                'waypoints': optimized_addresses,
                'original_addresses': addresses
            }
        
        except requests.exceptions.RequestException as e:
            print(f"[ERROR] Errore chiamata Google Maps API: {e}")
            return self._fallback_order(addresses)
        
        except Exception as e:
            print(f"[ERROR] Errore ottimizzazione route: {e}")
            return self._fallback_order(addresses)
    
    def _simple_route(self, addresses: List[str], start_location: str = None, end_location: str = None) -> Dict:
        """Route semplice per 1-2 indirizzi (no ottimizzazione necessaria)"""
        if not start_location:
            start_location = "Via Buon Pastore 52, 41125 Modena (MO)"
        
        if not end_location:
            end_location = start_location
        
        # Crea route: magazzino -> appartamenti -> magazzino
        full_route = [start_location] + addresses + [end_location]
        route_url = self._generate_maps_url(full_route)
        
        return {
            'success': True,
            'optimized_order': list(range(len(addresses))),
            'route_url': route_url,
            'total_distance_km': 0,
            'total_duration_minutes': 0,
            'waypoints': addresses,
            'original_addresses': addresses,
            'start_location': start_location,
            'end_location': end_location
        }
    
    def _fallback_order(self, addresses: List[str]) -> Dict:
        """Fallback: ordine originale se API fallisce"""
        print("[WARN] Usando ordine originale (API non disponibile)")
        
        route_url = self._generate_maps_url(addresses)
        
        return {
            'success': False,
            'optimized_order': list(range(len(addresses))),
            'route_url': route_url,
            'total_distance_km': 0,
            'total_duration_minutes': 0,
            'waypoints': addresses,
            'original_addresses': addresses,
            'error': 'API non disponibile - ordine non ottimizzato'
        }
    
    def _generate_maps_url(self, addresses: List[str], include_return: bool = False) -> str:
        """
        Genera URL Google Maps navigabile
        Formato: https://www.google.com/maps/dir/?api=1&origin=start&destination=end&waypoints=addr1|addr2&travelmode=driving
        
        Args:
            addresses: Lista indirizzi ottimizzati (solo appartamenti)
            include_return: Se True, ritorna al primo indirizzo alla fine
        """
        if not addresses or len(addresses) == 0:
            return ''
        
        # Encode indirizzi per URL
        from urllib.parse import quote
        
        if len(addresses) == 1:
            # Singolo indirizzo
            return f"https://www.google.com/maps/search/?api=1&query={quote(addresses[0])}"
        
        # Multi-stop route: primo indirizzo = origine, ultimo = destinazione
        origin = quote(addresses[0])
        
        # Se include_return, torniamo al primo indirizzo
        destination = quote(addresses[0] if include_return else addresses[-1])
        
        if len(addresses) > 2:
            # Waypoints intermedi (esclusi primo E ultimo indirizzo)
            # Se include_return è True, l'ultimo indirizzo è già il primo (ritorno), quindi escludiamo l'ultimo
            end_index = -1 if not include_return else len(addresses)
            waypoints = '|'.join([quote(addr) for addr in addresses[1:end_index]])
            url = f"https://www.google.com/maps/dir/?api=1&origin={origin}&destination={destination}&waypoints={waypoints}&travelmode=driving"
        else:
            # Solo origine e destinazione (2 indirizzi)
            url = f"https://www.google.com/maps/dir/?api=1&origin={origin}&destination={destination}&travelmode=driving"
        
        return url
    
    def optimize_tasks_route(self, tasks: List[Dict]) -> Tuple[List[Dict], Dict]:
        """
        Ottimizza ordine task basandosi su indirizzi
        
        Args:
            tasks: Lista task con campo 'indirizzo' o 'address'
        
        Returns:
            (tasks_ordinati, route_info)
        """
        # Estrai indirizzi
        addresses = []
        for task in tasks:
            addr = task.get('indirizzo') or task.get('address', '')
            if addr and addr.strip():
                addresses.append(addr.strip())
        
        if not addresses:
            print("[WARN] Nessun indirizzo valido nei task")
            return tasks, {'success': False, 'error': 'Nessun indirizzo'}
        
        # Ottimizza route
        route_info = self.optimize_route(addresses)
        
        if not route_info['success']:
            return tasks, route_info
        
        # Riordina tasks secondo ordine ottimizzato
        optimized_order = route_info['optimized_order']
        tasks_sorted = [tasks[i] for i in optimized_order if i < len(tasks)]
        
        return tasks_sorted, route_info
    
    def save_route_to_file(self, route_info: Dict, output_path: str = None) -> str:
        """
        Salva informazioni route in file JSON
        
        Args:
            route_info: Dizionario ritornato da optimize_route()
            output_path: Path file output (default: Operations_Reports/route_YYYY-MM-DD.json)
        
        Returns:
            Path file salvato
        """
        if not output_path:
            parent_dir = os.path.dirname(os.path.dirname(__file__))
            output_dir = os.path.join(parent_dir, 'Operations_Reports')
            os.makedirs(output_dir, exist_ok=True)
            
            date_str = datetime.now().strftime('%Y-%m-%d')
            output_path = os.path.join(output_dir, f'route_{date_str}.json')
        
        # Aggiungi timestamp
        route_data = {
            'generated_at': datetime.now().isoformat(),
            'date': datetime.now().strftime('%Y-%m-%d'),
            **route_info
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(route_data, f, indent=2, ensure_ascii=False)
        
        print(f"[OK] Route salvata: {output_path}")
        return output_path


# Utility function per testing rapido
def test_optimizer():
    """Test route optimizer con indirizzi di esempio"""
    optimizer = RouteOptimizer()
    
    test_addresses = [
        "Via Roma 10, Modena",
        "Viale Amendola 160, Modena",
        "Via Giuseppe Graziosi 143, Modena",
        "Via Michele Morelli 31, Modena"
    ]
    
    result = optimizer.optimize_route(test_addresses)
    
    print("\n" + "="*60)
    print("RISULTATO OTTIMIZZAZIONE")
    print("="*60)
    print(f"Success: {result['success']}")
    print(f"URL: {result['route_url']}")
    print(f"Distanza: {result.get('total_distance_km', 0)} km")
    print(f"Durata: {result.get('total_duration_minutes', 0)} min")
    print(f"Ordine ottimizzato: {result['optimized_order']}")
    
    return result


if __name__ == '__main__':
    test_optimizer()
