"""
Manequins vestidos e produtos da vitrine Track&Field.

As roupas são cascas da superfície do manequim: o corpo do MakeHuman (gerado por
gerar_manequins.py) traz em cada vértice a região do corpo ("_REGIAO") e a posição
ao longo do osso ("_T"). Cada peça escolhe as regiões que cobre, corta as bordas
(barra, punho, gola) e se afasta do corpo alguns milímetros, ou mais no caso da
jaqueta acolchoada. Malas e garrafa são modeladas por forma.

Cores e detalhes seguem as fotos do site tf.com.br. Os produtos "pretos" da marca
são, na foto, um azul-marinho muito escuro.
"""

import math
import os

import bpy  # precisa vir antes de bmesh e mathutils
import bmesh
from mathutils import Vector

PASTA = os.path.dirname(os.path.abspath(__file__))
MODELOS = os.path.join(PASTA, "modelos")
FONTE = os.path.join(PASTA, "fontes", "Outfit-Medium.ttf")

PELVE, LOMBAR, PEITO, CLAVICULA, BRACO, ANTEBRACO, MAO, COXA, PANTURRILHA, PE, PESCOCO, CABECA = range(12)

# Cores em RGB linear, medidas nas fotos dos produtos.
MARINHO_ESCURO = (0.0075, 0.0095, 0.022)
PRETO = (0.009, 0.009, 0.01)
AZUL_LASER = (0.022, 0.045, 0.15)
MARINHO_DUFFEL = (0.024, 0.031, 0.072)
GRAFITE = (0.018, 0.018, 0.022)
CAQUI = (0.2, 0.16, 0.11)


# ---------------------------------------------------------------- materiais

def _no(nt, tipo, **entradas):
    n = nt.nodes.new(tipo)
    for k, v in entradas.items():
        n.inputs[k].default_value = v
    return n


def material_tecido(nome, cor, textura="malha", rugosidade=0.75, brilho=0.15, ziper=False, escala=1.0):
    """Tecido esportivo. textura: "malha" (tricô fino), "perfurado" (furinhos),
    "nylon" (liso e acetinado) ou "chevron" (matelassê da duffel).
    Com ziper=True, uma faixa no centro da frente vira zíper (coordenadas do objeto)."""
    mat = bpy.data.materials.new(nome)
    mat.use_nodes = True
    nt = mat.node_tree
    bsdf = nt.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = (*cor, 1)
    bsdf.inputs["Roughness"].default_value = rugosidade
    bsdf.inputs["Sheen Weight"].default_value = brilho
    bsdf.inputs["Sheen Roughness"].default_value = 0.45
    coord = nt.nodes.new("ShaderNodeTexCoord")

    altura = None
    if textura == "malha":
        onda = _no(nt, "ShaderNodeTexWave", Scale=700 * escala, Distortion=1.5)
        onda.wave_type = "BANDS"
        onda.bands_direction = "Z"
        nt.links.new(coord.outputs["Object"], onda.inputs["Vector"])
        altura, forca = onda.outputs["Fac"], 0.06
    elif textura == "perfurado":
        furos = _no(nt, "ShaderNodeTexVoronoi", Scale=380 * escala)
        furos.feature = "F1"
        nt.links.new(coord.outputs["Object"], furos.inputs["Vector"])
        altura, forca = furos.outputs["Distance"], 0.12
    elif textura == "nylon":
        ruido = _no(nt, "ShaderNodeTexNoise", Scale=60 * escala, Detail=2.0)
        nt.links.new(coord.outputs["Object"], ruido.inputs["Vector"])
        altura, forca = ruido.outputs["Fac"], 0.04
    elif textura == "chevron":
        # Costuras em V: |x| somado a z, repetido.
        sep = nt.nodes.new("ShaderNodeSeparateXYZ")
        nt.links.new(coord.outputs["Object"], sep.inputs["Vector"])
        absx = _no(nt, "ShaderNodeMath")
        absx.operation = "ABSOLUTE"
        nt.links.new(sep.outputs["X"], absx.inputs[0])
        soma = _no(nt, "ShaderNodeMath")
        soma.operation = "ADD"
        nt.links.new(absx.outputs[0], soma.inputs[0])
        nt.links.new(sep.outputs["Z"], soma.inputs[1])
        mult = _no(nt, "ShaderNodeMath")
        mult.operation = "MULTIPLY"
        mult.inputs[1].default_value = 14 * escala
        nt.links.new(soma.outputs[0], mult.inputs[0])
        frac = _no(nt, "ShaderNodeMath")
        frac.operation = "PINGPONG"
        frac.inputs[1].default_value = 0.5
        nt.links.new(mult.outputs[0], frac.inputs[0])
        suave = _no(nt, "ShaderNodeMath")
        suave.operation = "POWER"
        suave.inputs[1].default_value = 0.35
        nt.links.new(frac.outputs[0], suave.inputs[0])
        altura, forca = suave.outputs[0], 0.9

    if altura is not None:
        relevo = _no(nt, "ShaderNodeBump", Strength=forca, Distance=0.006 if textura == "chevron" else 0.0004)
        nt.links.new(altura, relevo.inputs["Height"])
        nt.links.new(relevo.outputs["Normal"], bsdf.inputs["Normal"])

    if ziper:
        # Máscara: |x| < 4 mm e frente do corpo (y < 0).
        sep = nt.nodes.new("ShaderNodeSeparateXYZ")
        nt.links.new(coord.outputs["Object"], sep.inputs["Vector"])
        absx = _no(nt, "ShaderNodeMath")
        absx.operation = "ABSOLUTE"
        nt.links.new(sep.outputs["X"], absx.inputs[0])
        estreito = _no(nt, "ShaderNodeMath")
        estreito.operation = "LESS_THAN"
        estreito.inputs[1].default_value = 0.0035
        nt.links.new(absx.outputs[0], estreito.inputs[0])
        frente = _no(nt, "ShaderNodeMath")
        frente.operation = "LESS_THAN"
        frente.inputs[1].default_value = 0.0
        nt.links.new(sep.outputs["Y"], frente.inputs[0])
        mascara = _no(nt, "ShaderNodeMath")
        mascara.operation = "MULTIPLY"
        nt.links.new(estreito.outputs[0], mascara.inputs[0])
        nt.links.new(frente.outputs[0], mascara.inputs[1])
        cor_ziper = _no(nt, "ShaderNodeMix")
        cor_ziper.data_type = "RGBA"
        cor_ziper.inputs["A"].default_value = (*cor, 1)
        cor_ziper.inputs["B"].default_value = (0.004, 0.004, 0.005, 1)
        nt.links.new(mascara.outputs[0], cor_ziper.inputs["Factor"])
        nt.links.new(cor_ziper.outputs["Result"], bsdf.inputs["Base Color"])
        brilho_ziper = _no(nt, "ShaderNodeMapRange")
        brilho_ziper.inputs["To Min"].default_value = rugosidade
        brilho_ziper.inputs["To Max"].default_value = 0.3
        nt.links.new(mascara.outputs[0], brilho_ziper.inputs["Value"])
        nt.links.new(brilho_ziper.outputs["Result"], bsdf.inputs["Roughness"])
    return mat


def material_simples(nome, cor, rugosidade=0.5, metalico=0.0):
    mat = bpy.data.materials.new(nome)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = (*cor, 1)
    bsdf.inputs["Roughness"].default_value = rugosidade
    bsdf.inputs["Metallic"].default_value = metalico
    return mat


def criar_materiais():
    return {
        "manequim": material_simples("Manequim", (0.3, 0.3, 0.29), 0.45),
        "casaco": material_tecido("Casaco PowerCool", MARINHO_ESCURO, "perfurado", 0.7, 0.12, ziper=True),
        "bermuda_ciclista": material_tecido("Bermuda", MARINHO_ESCURO, "malha", 0.6, 0.2),
        "thermodry": material_tecido("Camiseta ThermoDry", MARINHO_ESCURO, "malha", 0.65, 0.18),
        "legging": material_tecido("Legging", PRETO, "malha", 0.55, 0.22),
        "shorts_laser": material_tecido("Shorts Laser", AZUL_LASER, "nylon", 0.55, 0.25),
        "sports": material_tecido("Camiseta Sports", MARINHO_ESCURO, "malha", 0.7, 0.12, escala=0.7),
        "jaqueta": material_tecido("Jaqueta Winter", PRETO, "nylon", 0.32, 0.3, ziper=True),
        "bermuda_caqui": material_tecido("Bermuda caqui", CAQUI, "malha", 0.8, 0.05, escala=0.5),
        "tenis_branco": material_simples("Tênis branco", (0.8, 0.8, 0.78), 0.55),
        "tenis_preto": material_simples("Tênis preto", (0.015, 0.015, 0.017), 0.5),
        "sola": material_simples("Sola", (0.85, 0.85, 0.83), 0.7),
        "refletivo": material_simples("Refletivo", (0.55, 0.56, 0.58), 0.25, 0.7),
        "logo_branco": material_simples("Logo branco", (0.85, 0.85, 0.85), 0.5),
        "duffel": material_tecido("Duffel matelassê", MARINHO_DUFFEL, "chevron", 0.45, 0.35),
        "duffel_liso": material_tecido("Duffel nylon", MARINHO_DUFFEL, "nylon", 0.45, 0.3),
        "fita": material_simples("Fita", (0.03, 0.038, 0.08), 0.6),
        "mala_trip": material_tecido("Mala Trip", PRETO, "nylon", 0.5, 0.15, escala=0.6),
        "garrafa": material_simples("Garrafa", GRAFITE, 0.42, 0.35),
        "aco": material_simples("Aço", (0.75, 0.74, 0.72), 0.25, 1.0),
        "metal_escuro": material_simples("Metal escuro", (0.05, 0.05, 0.055), 0.35, 1.0),
    }


# ---------------------------------------------------------------- manequim e cascas

class Manequim:
    """Manequim importado do .glb, com as regiões por vértice lidas para Python."""

    def __init__(self, arquivo, material):
        bpy.ops.import_scene.gltf(filepath=os.path.join(MODELOS, arquivo))
        obj = bpy.context.selected_objects[0]
        obj.parent = None
        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
        # O glTF triangula a malha e separa vértices nas costuras de UV. Junta os vértices
        # e refaz os quadrados: com triângulos a subdivisão gasta gigabytes de memória.
        bm = bmesh.new()
        bm.from_mesh(obj.data)
        bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
        bmesh.ops.join_triangles(bm, faces=bm.faces, angle_face_threshold=math.radians(40),
                                 angle_shape_threshold=math.radians(40))
        bm.to_mesh(obj.data)
        bm.free()
        while obj.data.uv_layers:
            obj.data.uv_layers.remove(obj.data.uv_layers[0])
        for p in obj.data.polygons:
            p.use_smooth = True
        obj.data.materials.clear()
        obj.data.materials.append(material)
        sub = obj.modifiers.new("Suavizar", "SUBSURF")
        sub.levels = sub.render_levels = 1
        self.obj = obj
        zs = [v.co.z for v in obj.data.vertices]
        self.altura = max(zs) - min(zs)

    def regiao(self, v):
        return round(self.obj.data.attributes["_REGIAO"].data[v].value)

    def t(self, v):
        return self.obj.data.attributes["_T"].data[v].value


def casca(manequim, nome, cobre, afastamento, material, espessura=0.0025, relaxar_bordas=6, deslocar=None):
    """Cria uma peça a partir da superfície do manequim.

    cobre(regiao, t, co) -> bool decide quais vértices entram na peça.
    afastamento: distância do corpo em metros (ou função de (regiao, t, co)).
    deslocar(co, normal) -> deslocamento extra, para gomos e volumes."""
    corpo = manequim.obj
    regioes = corpo.data.attributes["_REGIAO"].data
    ts = corpo.data.attributes["_T"].data
    bm = bmesh.new()
    bm.from_mesh(corpo.data)
    bm.verts.ensure_lookup_table()
    fora = [v for v in bm.verts if not cobre(round(regioes[v.index].value), ts[v.index].value, v.co)]
    bmesh.ops.delete(bm, geom=fora, context="VERTS")
    # Remove pedaços soltos pequenos (ilhas de poucos vértices).
    bm.verts.ensure_lookup_table()
    bm.normal_update()
    normais = {v: v.normal.copy() for v in bm.verts}
    for v in bm.verts:
        a = afastamento(v.co) if callable(afastamento) else afastamento
        extra = deslocar(v.co, normais[v]) if deslocar else 0.0
        v.co += normais[v] * (a + extra)
    # Endireita barras, punhos e golas.
    borda = [v for v in bm.verts if v.is_boundary]
    for _ in range(relaxar_bordas):
        bmesh.ops.smooth_vert(bm, verts=borda, factor=0.5, use_axis_x=True, use_axis_y=True, use_axis_z=True)
    malha = bpy.data.meshes.new(nome)
    bm.to_mesh(malha)
    bm.free()
    for atributo in list(malha.attributes):
        if atributo.name.startswith("_"):
            malha.attributes.remove(atributo)
    malha.materials.append(material)
    peca = bpy.data.objects.new(nome, malha)
    bpy.context.collection.objects.link(peca)
    for p in malha.polygons:
        p.use_smooth = True
    solido = peca.modifiers.new("Espessura", "SOLIDIFY")
    solido.thickness = espessura
    solido.offset = 1
    solido.use_rim = True
    sub = peca.modifiers.new("Suavizar", "SUBSURF")
    sub.levels = sub.render_levels = 1
    return peca


def logo(texto, tamanho, material, local, alvo, duas_linhas=False, girar_z=0.0):
    """Logo pequeno aplicado sobre uma peça (projetado na superfície pela frente)."""
    curva = bpy.data.curves.new("Logo", "FONT")
    curva.body = "Track\n&Field" if duas_linhas else texto
    if os.path.exists(FONTE):
        curva.font = bpy.data.fonts.load(FONTE, check_existing=True)
    curva.size = tamanho
    curva.align_x = "CENTER"
    curva.align_y = "CENTER"
    curva.space_line = 0.85
    obj = bpy.data.objects.new("Logo", curva)
    bpy.context.collection.objects.link(obj)
    obj.location = Vector(local) + Vector((0, -0.08, 0))
    obj.rotation_euler = (math.radians(90), 0, girar_z)
    obj.data.materials.append(material)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.ops.object.convert(target="MESH")
    obj = bpy.context.active_object
    envolver = obj.modifiers.new("Projetar", "SHRINKWRAP")
    envolver.target = alvo
    envolver.wrap_method = "PROJECT"
    envolver.use_project_y = True
    envolver.use_negative_direction = True
    envolver.use_positive_direction = True
    envolver.offset = 0.0012
    return obj


def acima(manequim, fracao):
    return manequim.altura * fracao


# ---------------------------------------------------------------- roupas por produto

def tenis(m, mats, cor="tenis_branco"):
    pecas = [casca(m, "Tênis", lambda r, t, co: r == PE or (r == PANTURRILHA and t > 0.94), 0.008, mats[cor], espessura=0.004)]
    pecas.append(casca(m, "Sola", lambda r, t, co: r == PE and co.z < 0.03, 0.011, mats["sola"], espessura=0.008, relaxar_bordas=2))
    return pecas


def vestir_casaco_powercool(m, mats):
    """Casaco feminino PowerCool: justo, gola alta, zíper inteiro, mangas até o punho,
    com bermuda de ciclista marinho (como na foto do site)."""
    h = m.altura
    barra = acima(m, 0.52)
    gola = acima(m, 0.845)
    casaco = casca(m, "Casaco PowerCool",
                   lambda r, t, co: (r in (PELVE, LOMBAR, PEITO, CLAVICULA, BRACO, COXA) and co.z > barra)
                   or (r == ANTEBRACO and t < 0.97) or (r == PESCOCO and co.z < gola),
                   lambda co: 0.007 if co.z < gola - 0.04 else 0.012, mats["casaco"], espessura=0.003)
    bermuda = casca(m, "Bermuda ciclista",
                    lambda r, t, co: r in (PELVE, LOMBAR, PEITO, COXA) and acima(m, 0.36) < co.z < acima(m, 0.56),
                    0.004, mats["bermuda_ciclista"])
    marca = logo("Track&Field", 0.012, mats["refletivo"], (0.055, 0, acima(m, 0.775)), casaco, duas_linhas=True)
    return [casaco, bermuda, marca] + tenis(m, mats)


def vestir_thermodry(m, mats):
    """Camiseta feminina ThermoDry Gota: justa, decote canoa, manga curta e recorte em
    gota nas costas; com legging preta."""
    h = m.altura
    barra = acima(m, 0.54)  # desce por cima do cós da peça de baixo
    pescoco = acima(m, 0.83)

    def cobre(r, t, co):
        if r in (MAO, ANTEBRACO, PANTURRILHA, PE, CABECA):
            return False
        if r == BRACO:
            return t < 0.38
        if co.z < barra or co.z > pescoco:
            return False
        if co.y < 0 and co.z > acima(m, 0.8) and abs(co.x) < 0.06:
            return False  # decote
        if co.y > 0 and abs(co.x) < 0.035 and acima(m, 0.69) < co.z < acima(m, 0.77):
            return False  # gota nas costas
        return True

    camiseta = casca(m, "Camiseta ThermoDry", cobre, lambda co: 0.006 + max(0.0, acima(m, 0.64) - co.z) * 0.12, mats["thermodry"])
    legging = casca(m, "Legging", lambda r, t, co: r in (PELVE, LOMBAR, PEITO, COXA) and co.z < acima(m, 0.585) or (r == PANTURRILHA and t < 0.9),
                    0.004, mats["legging"])
    marca = logo("Track&Field", 0.011, mats["refletivo"], (0.05, 0, acima(m, 0.765)), camiseta, duas_linhas=True)
    return [camiseta, legging, marca] + tenis(m, mats)


def camiseta_sports(m, mats, mat="sports"):
    """Camiseta masculina Sports: justa, gola careca, logo refletivo no peito e faixa
    refletiva na barra da manga."""
    barra = acima(m, 0.54)  # desce por cima do cós da peça de baixo
    pescoco = acima(m, 0.848)  # gola careca, rente à base do pescoço

    def cobre(r, t, co):
        if r == BRACO:
            return t < 0.42
        if r in (PELVE, LOMBAR, PEITO, CLAVICULA, COXA, PESCOCO):
            return barra < co.z < pescoco
        return False

    camiseta = casca(m, "Camiseta Sports", cobre, lambda co: 0.007 + max(0.0, acima(m, 0.64) - co.z) * 0.14, mats[mat])
    faixa = casca(m, "Faixa refletiva", lambda r, t, co: r == BRACO and 0.36 < t < 0.41, 0.0085, mats["refletivo"], relaxar_bordas=3)
    marca = logo("Track&Field", 0.012, mats["refletivo"], (0.07, 0, acima(m, 0.765)), camiseta, duas_linhas=True)
    return [camiseta, faixa, marca]


def vestir_shorts_laser(m, mats):
    """Shorts masculino Laser azul, solto e curto, com camiseta Sports (foto do site)."""
    cintura = acima(m, 0.585)

    virilha = acima(m, 0.475)

    def folga(co):
        # Justo na cintura e na virilha, mais solto nas pernas, como shorts de corrida.
        return 0.007 + max(0.0, virilha - co.z) * 0.32

    shorts = casca(m, "Shorts Laser", lambda r, t, co: r in (PELVE, LOMBAR, PEITO, COXA) and acima(m, 0.4) < co.z < cintura,
                   folga, mats["shorts_laser"], espessura=0.003)
    marca = logo("Track&Field", 0.012, mats["logo_branco"], (-0.13, 0, acima(m, 0.425)), shorts, duas_linhas=True)
    return [shorts, marca] + camiseta_sports(m, mats) + tenis(m, mats, "tenis_preto")


def vestir_jaqueta_winter(m, mats):
    """Jaqueta masculina Winter: acolchoada em gomos horizontais, gola alta e zíper,
    com bermuda caqui (foto do site)."""
    barra = acima(m, 0.525)
    gola = acima(m, 0.86)
    gomo = 0.085

    def volume(co, normal):
        # Gomos: estufa entre as costuras horizontais.
        fase = (co.z % gomo) / gomo
        return 0.022 * math.sin(math.pi * fase) ** 0.6

    jaqueta = casca(m, "Jaqueta Winter",
                    lambda r, t, co: (r in (PELVE, LOMBAR, PEITO, CLAVICULA, BRACO, COXA) and co.z > barra)
                    or (r == ANTEBRACO and t < 0.95) or (r == PESCOCO and co.z < gola),
                    0.016, mats["jaqueta"], espessura=0.004, deslocar=volume)
    bermuda = casca(m, "Bermuda caqui", lambda r, t, co: r in (PELVE, LOMBAR, PEITO, COXA) and acima(m, 0.37) < co.z < acima(m, 0.575),
                    lambda co: 0.007 + max(0.0, acima(m, 0.475) - co.z) * 0.22, mats["bermuda_caqui"])
    return [jaqueta, bermuda] + tenis(m, mats, "tenis_preto")


def vestir_sports(m, mats):
    """Camiseta Sports com legging de corrida preta."""
    legging = casca(m, "Legging", lambda r, t, co: r in (PELVE, LOMBAR, PEITO, COXA) and co.z < acima(m, 0.585) or (r == PANTURRILHA and t < 0.9),
                    0.004, mats["legging"])
    return camiseta_sports(m, mats) + [legging] + tenis(m, mats, "tenis_preto")


# ---------------------------------------------------------------- produtos sobre os cubos

def _curva_tubo(nome, pontos, raio, material):
    curva = bpy.data.curves.new(nome, "CURVE")
    curva.dimensions = "3D"
    curva.bevel_depth = raio
    curva.bevel_resolution = 3
    spline = curva.splines.new("BEZIER")
    spline.bezier_points.add(len(pontos) - 1)
    for bp, p in zip(spline.bezier_points, pontos):
        bp.co = p
        bp.handle_left_type = bp.handle_right_type = "AUTO"
    obj = bpy.data.objects.new(nome, curva)
    bpy.context.collection.objects.link(obj)
    obj.data.materials.append(material)
    return obj


def fita_plana(nome, pontos, largura, lado, material, espessura=0.003, passos=24):
    """Fita de tecido (alça, webbing): faixa plana que passa pelos pontos (curva suave),
    com a largura na direção `lado`. Com lado=None a fita fica de frente para quem olha
    da vitrine (largura perpendicular à curva, no plano XZ), como nas fotos."""
    bez = _curva_tubo("tmp", pontos, 0, material)
    bez.data.resolution_u = passos
    deps = bpy.context.evaluated_depsgraph_get()
    linha = bez.evaluated_get(deps).to_mesh()
    centro = [v.co.copy() for v in linha.vertices]
    bez.evaluated_get(deps).to_mesh_clear()
    bpy.data.objects.remove(bez)
    bm = bmesh.new()
    pares = []
    for k, c in enumerate(centro):
        if lado is None:
            tangente = (centro[min(k + 1, len(centro) - 1)] - centro[max(k - 1, 0)]).normalized()
            d = tangente.cross(Vector((0, 1, 0))).normalized() * largura / 2
        else:
            d = Vector(lado).normalized() * largura / 2
        pares.append((bm.verts.new(c - d), bm.verts.new(c + d)))
    for (a, b), (c, d) in zip(pares, pares[1:]):
        bm.faces.new((a, b, d, c))
    malha = bpy.data.meshes.new(nome)
    bm.to_mesh(malha)
    bm.free()
    malha.materials.append(material)
    obj = bpy.data.objects.new(nome, malha)
    bpy.context.collection.objects.link(obj)
    solido = obj.modifiers.new("Espessura", "SOLIDIFY")
    solido.thickness = espessura
    solido.offset = 0
    b = obj.modifiers.new("Bisel", "BEVEL")
    b.width = espessura * 0.4
    b.segments = 2
    for f in malha.polygons:
        f.use_smooth = True
    return obj


def faixa_em_volta(nome, alvo, x, raio, largura, material, afastamento=0.003):
    """Faixa que dá a volta no corpo de uma mala (plano YZ em x), colada na superfície."""
    bpy.ops.mesh.primitive_cylinder_add(vertices=96, radius=raio, depth=largura, end_fill_type="NOTHING",
                                        location=(x, 0, 0.15), rotation=(0, math.radians(90), 0))
    faixa = bpy.context.active_object
    faixa.name = nome
    faixa.data.materials.append(material)
    envolver = faixa.modifiers.new("Colar", "SHRINKWRAP")
    envolver.target = alvo
    envolver.wrap_method = "NEAREST_SURFACEPOINT"
    envolver.offset = afastamento
    solido = faixa.modifiers.new("Espessura", "SOLIDIFY")
    solido.thickness = 0.002
    for f in faixa.data.polygons:
        f.use_smooth = True
    return faixa


def mala_duffel(mats):
    """Mala Duffel Matelassê azul-noturno: corpo macio em chevron, duas fitas que dão a
    volta na mala, alças de mão e alça transversal larga."""
    bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 0, 0.15))
    corpo = bpy.context.active_object
    corpo.name = "Duffel"
    corpo.scale = (0.54, 0.27, 0.3)
    bpy.ops.object.transform_apply(scale=True)
    corpo.data.materials.append(mats["duffel"])
    bis = corpo.modifiers.new("Bisel", "BEVEL")
    bis.width = 0.1
    bis.segments = 6
    bpy.ops.object.modifier_apply(modifier=bis.name)
    # Topo mais estreito que a base e laterais levemente cedidas.
    for v in corpo.data.vertices:
        f = (v.co.z) / 0.3
        v.co.y *= 1.0 - 0.22 * max(0.0, f - 0.4)
        v.co.x *= 1.0 - 0.06 * max(0.0, f - 0.5)
    sub = corpo.modifiers.new("Suavizar", "SUBSURF")
    sub.levels = sub.render_levels = 2
    for p in corpo.data.polygons:
        p.use_smooth = True

    pecas = [corpo]
    for x in (-0.13, 0.13):
        pecas.append(faixa_em_volta("Fita", corpo, x, 0.22, 0.03, mats["fita"]))
    for y in (-0.075, 0.075):
        pecas.append(fita_plana("Alça de mão", [(-0.13, y, 0.27), (-0.1, y, 0.37), (0.1, y, 0.37), (0.13, y, 0.27)],
                                0.024, None, mats["fita"], 0.008))
    pecas.append(fita_plana("Alça transversal", [(-0.27, 0.02, 0.17), (-0.25, 0.08, 0.42), (0.0, 0.14, 0.6),
                                                 (0.25, 0.08, 0.42), (0.27, 0.02, 0.17)], 0.034, None, mats["fita"], 0.004))
    for x in (-0.13, 0.13):
        marca = texto_plano("Track&Field", 0.016, mats["refletivo"], (x, -0.15, 0.13), girar=90)
        envolver = marca.modifiers.new("Colar", "SHRINKWRAP")
        envolver.target = corpo
        envolver.offset = 0.0055
        pecas.append(marca)
    return pecas


def mala_trip(mats):
    """Mala Trip preta: mochila conversível retangular, com bolso frontal de zíper em
    diagonal, alça de mão no topo e alças de ombro acolchoadas nas costas."""
    bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 0, 0.24))
    corpo = bpy.context.active_object
    corpo.name = "Mala Trip"
    corpo.scale = (0.32, 0.18, 0.48)
    bpy.ops.object.transform_apply(scale=True)
    corpo.data.materials.append(mats["mala_trip"])
    bis = corpo.modifiers.new("Bisel", "BEVEL")
    bis.width = 0.05
    bis.segments = 5
    sub = corpo.modifiers.new("Suavizar", "SUBSURF")
    sub.levels = sub.render_levels = 1
    for p in corpo.data.polygons:
        p.use_smooth = True
    bpy.ops.mesh.primitive_cube_add(size=1, location=(0, -0.093, 0.26))
    bolso = bpy.context.active_object
    bolso.scale = (0.27, 0.025, 0.34)
    bpy.ops.object.transform_apply(scale=True)
    bolso.data.materials.append(mats["mala_trip"])
    b2 = bolso.modifiers.new("Bisel", "BEVEL")
    b2.width = 0.03
    b2.segments = 5
    for p in bolso.data.polygons:
        p.use_smooth = True
    ziper = _curva_tubo("Zíper", [(-0.12, -0.107, 0.11), (-0.05, -0.108, 0.3), (0.02, -0.107, 0.42)], 0.0022, mats["metal_escuro"])
    puxador = caixa_simples("Puxador", (0.02, -0.11, 0.405), (0.008, 0.004, 0.03), mats["metal_escuro"])
    alca = fita_plana("Alça de mão", [(-0.06, 0.0, 0.475), (-0.045, 0.0, 0.53), (0.045, 0.0, 0.53), (0.06, 0.0, 0.475)],
                      0.03, (0, 1, 0), mats["fita"], 0.008)
    pecas = [corpo, bolso, ziper, puxador, alca]
    for x in (-0.085, 0.085):
        pecas.append(fita_plana("Alça de ombro", [(x, 0.09, 0.43), (x * 1.1, 0.13, 0.33), (x * 1.25, 0.13, 0.14), (x * 1.3, 0.1, 0.06)],
                                0.055, (1, 0, 0), mats["mala_trip"], 0.02))
    marca = texto_plano("Track&Field", 0.017, mats["refletivo"], (0.0, -0.107, 0.07))
    pecas.append(marca)
    return pecas


def caixa_simples(nome, local, tamanho, material):
    bpy.ops.mesh.primitive_cube_add(size=1, location=local)
    obj = bpy.context.active_object
    obj.name = nome
    obj.scale = tamanho
    bpy.ops.object.transform_apply(scale=True)
    obj.data.materials.append(material)
    return obj


def garrafa_urban(mats):
    """Garrafa Urban 950 ml: aço com pintura grafite fosca, anel metálico no gargalo,
    tampa com alça e logo vertical."""
    perfil = [(0.0, 0.0), (0.040, 0.0), (0.042, 0.004), (0.042, 0.215), (0.039, 0.232), (0.03, 0.248),
              (0.024, 0.256), (0.024, 0.262)]
    malha = bpy.data.meshes.new("Garrafa")
    bm = bmesh.new()
    anel = [bm.verts.new((r, 0, z)) for r, z in perfil]
    for a, b in zip(anel, anel[1:]):
        bm.edges.new((a, b))
    bmesh.ops.spin(bm, geom=bm.verts[:] + bm.edges[:], axis=(0, 0, 1), cent=(0, 0, 0), steps=64, angle=math.tau)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-6)
    bm.to_mesh(malha)
    bm.free()
    corpo = bpy.data.objects.new("Garrafa", malha)
    bpy.context.collection.objects.link(corpo)
    malha.materials.append(mats["garrafa"])
    for p in malha.polygons:
        p.use_smooth = True
    bpy.ops.mesh.primitive_cylinder_add(vertices=64, radius=0.026, depth=0.012, location=(0, 0, 0.268))
    aro = bpy.context.active_object
    aro.data.materials.append(mats["aco"])
    bpy.ops.mesh.primitive_cylinder_add(vertices=64, radius=0.027, depth=0.022, location=(0, 0, 0.285))
    tampa = bpy.context.active_object
    tampa.data.materials.append(mats["garrafa"])
    b = tampa.modifiers.new("Bisel", "BEVEL")
    b.width = 0.004
    b.segments = 3
    bpy.ops.mesh.primitive_torus_add(major_radius=0.02, minor_radius=0.0045, location=(0, 0, 0.312), rotation=(math.radians(90), 0, 0))
    alca = bpy.context.active_object
    alca.data.materials.append(mats["garrafa"])
    for o in (aro, tampa, alca):
        for p in o.data.polygons:
            p.use_smooth = True
    marca = texto_plano("Track&Field", 0.017, mats["logo_branco"], (0.0, -0.0425, 0.08), girar=90)
    envolver = marca.modifiers.new("Projetar", "SHRINKWRAP")
    envolver.target = corpo
    envolver.offset = 0.0004
    return [corpo, aro, tampa, alca, marca]


def texto_plano(texto, tamanho, material, local, girar=0):
    curva = bpy.data.curves.new("Marca", "FONT")
    curva.body = texto
    if os.path.exists(FONTE):
        curva.font = bpy.data.fonts.load(FONTE, check_existing=True)
    curva.size = tamanho
    curva.align_x = "CENTER"
    curva.align_y = "CENTER"
    curva.extrude = 0.0004
    obj = bpy.data.objects.new("Marca", curva)
    bpy.context.collection.objects.link(obj)
    obj.location = local
    obj.rotation_euler = (math.radians(90), math.radians(girar), 0)
    obj.data.materials.append(material)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.ops.object.convert(target="MESH")
    return bpy.context.active_object


# ---------------------------------------------------------------- catálogo das paradas

VESTIR = {
    "Casaco PowerCool": ("manequim-feminino.glb", vestir_casaco_powercool),
    "Camiseta ThermoDry": ("manequim-feminino.glb", vestir_thermodry),
    "Shorts Laser": ("manequim-masculino.glb", vestir_shorts_laser),
    "Jaqueta Winter": ("manequim-masculino.glb", vestir_jaqueta_winter),
    "Camiseta Sports": ("manequim-masculino.glb", vestir_sports),
}

# Produto sobre cubo: (montagem, altura do cubo, lente da câmera, altura do produto, giro em graus).
SOBRE_CUBO = {
    "Mala Duffel Matelassê": (mala_duffel, 0.62, 70, 0.34, -16),
    "Mala Trip": (mala_trip, 0.55, 65, 0.5, -28),
    "Garrafa Urban 950 ml": (garrafa_urban, 0.95, 90, 0.31, -10),
}


def montar_produto(produto, mats):
    """Monta o produto de uma parada e devolve (objetos, altura do pedestal ou None)."""
    if produto in VESTIR:
        arquivo, vestir = VESTIR[produto]
        m = Manequim(arquivo, mats["manequim"])
        return [m.obj] + vestir(m, mats), None
    montar, pedestal = SOBRE_CUBO[produto][:2]
    return montar(mats), pedestal
