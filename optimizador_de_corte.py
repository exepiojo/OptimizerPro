from pulp import *
import matplotlib.pyplot as plt
import sys
import subprocess

# Verificar instalación de dependencias
try:
    from pulp import *
    import matplotlib.pyplot as plt
except ImportError:
    print("\nInstalando dependencias necesarias...\n")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pulp", "matplotlib"])
    print("\nVuelve a ejecutar el script después de la instalación.\n")
    sys.exit()

# Configuración de datos
nombres_articulos = ['A', 'B', 'C', 'D', 'E']
articulos = [100, 300, 150, 400, 1111]
cantidad_articulos = [5, 10, 8, 3, 5]
largo_material = 2000
colores = {'A': 'red', 'B': 'green', 'C': 'blue', 'D': 'orange', 'E': 'purple'}

# Configurar y resolver el modelo
prob = LpProblem("Problema_Corte", LpMinimize)
y = LpVariable.dicts("BarraEnUso", range(100), 0, 1, LpInteger)
x = LpVariable.dicts("Cantidad", [(i,j) for i in range(5) for j in range(100)], 0, None, LpInteger)

prob += lpSum(y[j] for j in range(100))

for i in range(5):
    prob += lpSum(x[(i,j)] for j in range(100)) >= cantidad_articulos[i]

for j in range(100):
    prob += lpSum(x[(i,j)] * articulos[i] for i in range(5)) <= largo_material * y[j]

prob.solve()

# Procesar resultados
barras = []
if LpStatus[prob.status] == "Optimal":
    for j in range(100):
        if value(y[j]) == 1:
            barra_actual = []
            for i in range(5):
                if value(x[(i,j)]) > 0:
                    barra_actual.extend([(nombres_articulos[i], articulos[i])] * int(value(x[(i,j)])))
            barras.append(barra_actual)

# Visualización
if barras:
    # Calcular y ordenar por desperdicio
    barras_con_desperdicio = []
    for barra in barras:
        total_usado = sum(longitud for (_, longitud) in barra)
        desperdicio = largo_material - total_usado
        barras_con_desperdicio.append((desperdicio, barra))
    
    barras_con_desperdicio.sort(key=lambda x: x[0])
    barras_ordenadas = [barra for (desperdicio, barra) in barras_con_desperdicio]
    desperdicios = [desperdicio for (desperdicio, barra) in barras_con_desperdicio]

    # Configuración de diseño
    bar_height = 0.6
    spacing = 1.0
    fig, ax = plt.subplots(figsize=(14, 6 + len(barras_ordenadas)*0.4))
    
    # Dibujar barras
    y_positions = []
    for idx, (barra, desperdicio) in enumerate(zip(barras_ordenadas, desperdicios)):
        y_pos = idx * (bar_height + spacing)
        y_positions.append(y_pos)
        posicion = 0
        
        for articulo, longitud in barra:
            ax.barh(y_pos, longitud, left=posicion, height=bar_height,
                    color=colores[articulo], edgecolor='black', linewidth=0.8)
            
            # Texto del artículo
            if longitud >= 100:
                ax.text(posicion + longitud/2, y_pos + bar_height/2,
                        f'{articulo}\n({longitud})',
                        ha='center', va='center',
                        color='black', fontsize=9, fontweight='bold')
            
            posicion += longitud
        
        # Texto de desperdicio
        ax.text(largo_material + 50, y_pos + bar_height/2,
                f'Desperdicio: {desperdicio}',
                ha='left', va='center',
                color='black', fontsize=10, fontweight='bold')

    # Configuración del gráfico
    ax.set_xlim(0, largo_material * 1.2)
    ax.set_ylim(min(y_positions) - bar_height, max(y_positions) + bar_height)
    ax.set_yticks([y_pos + bar_height/2 for y_pos in y_positions])
    ax.set_yticklabels([f'Barra {j+1}' for j in range(len(barras_ordenadas))], fontsize=10)
    ax.set_xlabel('Longitud Utilizada (mm)', fontsize=12, fontweight='bold')
    ax.set_title('Distribución de Cortes - Ordenado por Menor Desperdicio', 
                pad=20, fontsize=14, fontweight='bold')
    
    # Estilos adicionales
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.grid(axis='x', linestyle='--', alpha=0.3)

    # Leyenda
    handles = [plt.Rectangle((0,0),1,1, color=colores[art], edgecolor='black') 
              for art in nombres_articulos]
    ax.legend(handles, nombres_articulos, 
             title="Artículos", loc='center left',
             bbox_to_anchor=(1, 0.5), frameon=True,
             edgecolor='black', title_fontproperties={'weight':'bold'})

    plt.tight_layout()
    plt.show()
else:
    print("\nNo hay barras para mostrar. Verifica los datos de entrada.")