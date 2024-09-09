import requests
import pandas as pd
import folium
from geopy.geocoders import Nominatim
import math

# Função para obter coordenadas por endereço
def obter_coordenadas_por_endereco(endereco):
    geolocator = Nominatim(user_agent="autopecas_locator")
    try:
        location = geolocator.geocode(endereco, timeout=10)
        if location:
            return location.latitude, location.longitude
        else:
            print(f"Endereço não encontrado: {endereco}")
            return None, None
    except Exception as e:
        print(f"Erro ao buscar coordenadas para o endereço {endereco}: {e}")
        return None, None

# Função para calcular a caixa delimitadora
def calcular_caixa_delimitadora(lat, lon, raio_km):
    delta_lat = raio_km / 111  # Aproximadamente 111 km por grau de latitude
    delta_lon = raio_km / (111 * abs(math.cos(math.radians(lat))))  # Correção para a longitude
    
    lat_min = lat - delta_lat
    lat_max = lat + delta_lat
    lon_min = lon - delta_lon
    lon_max = lon + delta_lon
    
    return lat_min, lon_min, lat_max, lon_max

# Função para obter endereço por coordenadas usando a geolocalização reversa
def obter_endereco_por_coordenadas(lat, lon):
    geolocator = Nominatim(user_agent="autopecas_locator")
    try:
        location = geolocator.reverse((lat, lon), timeout=10)
        return location.address if location else 'Endereço não disponível'
    except Exception as e:
        print(f"Erro ao buscar o endereço para as coordenadas {lat}, {lon}: {e}")
        return 'Endereço não disponível'

def gerar_mapa(df):
    mapa = folium.Map(location=[lat_central, lon_central], zoom_start=12)
    for _, row in df.iterrows():
        latitude = row['Latitude']
        longitude = row['Longitude']
        
        if pd.notna(latitude) and pd.notna(longitude) and latitude != 'Não disponível' and longitude != 'Não disponível':
            try:
                lat = float(latitude)
                lon = float(longitude)
                
                nome = row['Nome']
                endereco = row['Endereço'] if row['Endereço'] != 'Não disponível' else obter_endereco_por_coordenadas(lat, lon)
                telefone = row['Telefone']
                
                folium.Marker(
                    location=[lat, lon],
                    popup=f"<b>{nome}</b><br>Endereço: {endereco}<br>Telefone: {telefone}",
                    icon=folium.Icon(icon="car", prefix="fa")
                ).add_to(mapa)
            except ValueError:
                print(f"Erro ao converter valores de latitude/longitude para {nome}.")
    
    mapa.save("mapa_autopecas_belo_horizonte.html")
    print("Mapa gerado com sucesso!")

def buscar_empresas_autopecas(lat_central, lon_central, raio_km):
    lat_min, lon_min, lat_max, lon_max = calcular_caixa_delimitadora(lat_central, lon_central, raio_km)
    
    url = "http://overpass-api.de/api/interpreter"
    query = f"""
    [out:json];
    (
      node["shop"="car_parts"]({lat_min},{lon_min},{lat_max},{lon_max});
    );
    out body;
    """
    try:
        response = requests.get(url, params={'data': query})
        if response.status_code == 200:
            dados = response.json()
            return dados
        else:
            print(f"Erro ao buscar dados da API: {response.status_code}")
            return None
    except Exception as e:
        print(f"Erro ao buscar dados: {e}")
        return None

def processar_dados_empresas(dados):
    empresas = []
    if 'elements' in dados:
        for elemento in dados['elements']:
            nome = elemento.get('tags', {}).get('name', 'Nome não disponível')
            endereco = elemento.get('tags', {}).get('addr:street', 'Não disponível')
            telefone = elemento.get('tags', {}).get('contact:phone', 'Telefone não disponível')
            latitude = elemento.get('lat', 'Não disponível')
            longitude = elemento.get('lon', 'Não disponível')
            
            if endereco != 'Não disponível':  # Filtra apenas empresas com endereço
                empresas.append({
                    'Nome': nome,
                    'Endereço': endereco,
                    'Telefone': telefone,
                    'Latitude': latitude,
                    'Longitude': longitude
                })
    
    return pd.DataFrame(empresas)

def main():
    endereco_central = "Avenida Dom Pedro I, 402, Itapoã, Belo Horizonte"
    global lat_central, lon_central
    lat_central, lon_central = obter_coordenadas_por_endereco(endereco_central)
    
    if lat_central and lon_central:
        raio_km = 20
        dados = buscar_empresas_autopecas(lat_central, lon_central, raio_km)
        
        if dados:
            df = processar_dados_empresas(dados)
            
            if not df.empty:
                print("Empresas encontradas:")
                print(df)
                gerar_mapa(df)
            else:
                print("Nenhuma empresa foi encontrada.")
        else:
            print("Falha ao obter os dados da API.")
    else:
        print("Não foi possível obter as coordenadas para o endereço fornecido.")

if __name__ == "__main__":
    main()

