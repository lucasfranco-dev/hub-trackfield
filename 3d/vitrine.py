"""
Vitrine Track&Field em 3D, montada por script no Blender.

Uso (Blender como módulo Python, `pip install bpy==5.2.2`):

    python 3d/vitrine.py --parada 0 --largura 1600 --altura 1200 --amostras 256 --saida 3d/renders/parada-0.png
    python 3d/vitrine.py --parada 0 --previa          # 480x360, poucas amostras, para testar

Eixos: X ao longo da vitrine (esquerda para a direita de quem olha), Y para dentro
da loja, Z para cima. O vidro fica em y = 0 e a câmera, do lado de fora (y < 0).
Medidas em metros.
"""

import argparse
import math
import os
import sys

import bpy  # precisa vir antes de bmesh e mathutils
import bmesh
from mathutils import Vector

PASTA = os.path.dirname(os.path.abspath(__file__))
TEXTURAS = os.path.join(PASTA, "texturas")
FONTE = os.path.join(PASTA, "fontes", "Outfit-Medium.ttf")

# Paradas da vitrine, na mesma ordem da planilha. Na fase 3 cada uma ganha seu produto.
ESPACO_PARADAS = 1.5
PARADAS = [
    {"tipo": "manequim", "produto": "Casaco PowerCool"},
    {"tipo": "cubo", "produto": "Mala Duffel Matelassê"},
    {"tipo": "manequim", "produto": "Camiseta ThermoDry"},
    {"tipo": "manequim", "produto": "Shorts Laser"},
    {"tipo": "manequim", "produto": "Jaqueta Winter"},
    {"tipo": "cubo", "produto": "Mala Trip"},
    {"tipo": "manequim", "produto": "Camiseta Sports"},
    {"tipo": "cubo", "produto": "Garrafa Urban 950 ml"},
]

PISO_VITRINE = 0.10      # altura do piso da vitrine acima do corredor do shopping
FUNDO_Y = 2.3            # parede do fundo
TETO_Z = 3.0
FACHADA_TOPO = 3.9
INICIO_X = -3.5
FIM_X = (len(PARADAS) - 1) * ESPACO_PARADAS + 3.5

LUZ_QUENTE = (1.0, 0.83, 0.64)


# ---------------------------------------------------------------- utilidades

def limpar_cena():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def caixa(nome, centro, tamanho, material=None):
    bpy.ops.mesh.primitive_cube_add(size=1, location=centro)
    obj = bpy.context.active_object
    obj.name = nome
    obj.scale = tamanho
    bpy.ops.object.transform_apply(scale=True)
    if material:
        obj.data.materials.append(material)
    return obj


def plano(nome, centro, tamanho, rotacao=(0, 0, 0), material=None):
    bpy.ops.mesh.primitive_plane_add(size=1, location=centro, rotation=rotacao)
    obj = bpy.context.active_object
    obj.name = nome
    obj.scale = (tamanho[0], tamanho[1], 1)
    bpy.ops.object.transform_apply(scale=True)
    if material:
        obj.data.materials.append(material)
    return obj


def suavizar(obj):
    for p in obj.data.polygons:
        p.use_smooth = True


# ---------------------------------------------------------------- materiais

def material_basico(nome, cor, rugosidade=0.5, metalico=0.0, brilho_tecido=0.0):
    mat = bpy.data.materials.new(nome)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = (*cor, 1)
    bsdf.inputs["Roughness"].default_value = rugosidade
    bsdf.inputs["Metallic"].default_value = metalico
    if brilho_tecido:
        bsdf.inputs["Sheen Weight"].default_value = brilho_tecido
        bsdf.inputs["Sheen Roughness"].default_value = 0.5
    return mat


def material_textura(nome, prefixo, escala=1.0, tom=(1, 1, 1), rugosidade_mult=1.0):
    """Material PBR com as texturas CC0 do Poly Haven (cor, normal e rugosidade)."""
    mat = bpy.data.materials.new(nome)
    mat.use_nodes = True
    nt = mat.node_tree
    n = nt.nodes
    bsdf = n["Principled BSDF"]

    coord = n.new("ShaderNodeTexCoord")
    mapa = n.new("ShaderNodeMapping")
    mapa.inputs["Scale"].default_value = (escala, escala, escala)
    nt.links.new(coord.outputs["UV"], mapa.inputs["Vector"])

    def imagem(sufixo, cor):
        caminho = os.path.join(TEXTURAS, f"{prefixo}_{sufixo}_2k.jpg")
        tex = n.new("ShaderNodeTexImage")
        tex.image = bpy.data.images.load(caminho, check_existing=True)
        tex.image.colorspace_settings.name = "sRGB" if cor else "Non-Color"
        nt.links.new(mapa.outputs["Vector"], tex.inputs["Vector"])
        return tex

    dif = imagem("diff", True)
    tingir = n.new("ShaderNodeMix")
    tingir.data_type = "RGBA"
    tingir.blend_type = "MULTIPLY"
    tingir.inputs["Factor"].default_value = 1.0
    tingir.inputs["B"].default_value = (*tom, 1)
    nt.links.new(dif.outputs["Color"], tingir.inputs["A"])
    nt.links.new(tingir.outputs["Result"], bsdf.inputs["Base Color"])

    rug = imagem("rough", False)
    mult = n.new("ShaderNodeMath")
    mult.operation = "MULTIPLY"
    mult.inputs[1].default_value = rugosidade_mult
    nt.links.new(rug.outputs["Color"], mult.inputs[0])
    nt.links.new(mult.outputs["Value"], bsdf.inputs["Roughness"])

    nor = imagem("nor_gl", False)
    nmap = n.new("ShaderNodeNormalMap")
    nt.links.new(nor.outputs["Color"], nmap.inputs["Color"])
    nt.links.new(nmap.outputs["Normal"], bsdf.inputs["Normal"])
    return mat


def material_vidro():
    """Vidro fino: deixa passar a luz e reflete conforme o ângulo, sem distorcer."""
    mat = bpy.data.materials.new("Vidro")
    mat.use_nodes = True
    nt = mat.node_tree
    n = nt.nodes
    n.remove(n["Principled BSDF"])
    saida = n["Material Output"]
    transparente = n.new("ShaderNodeBsdfTransparent")
    transparente.inputs["Color"].default_value = (0.94, 0.97, 0.96, 1)
    reflexo = n.new("ShaderNodeBsdfGlossy")
    reflexo.inputs["Roughness"].default_value = 0.02
    peso = n.new("ShaderNodeLayerWeight")
    peso.inputs["Blend"].default_value = 0.12
    mistura = n.new("ShaderNodeMixShader")
    nt.links.new(peso.outputs["Fresnel"], mistura.inputs["Fac"])
    nt.links.new(transparente.outputs[0], mistura.inputs[1])
    nt.links.new(reflexo.outputs[0], mistura.inputs[2])
    nt.links.new(mistura.outputs[0], saida.inputs["Surface"])
    return mat


def material_tecido(nome, cor, escala_malha=900.0):
    """Malha esportiva: cor escura, brilho de tecido e um relevo fino de tricô."""
    mat = material_basico(nome, cor, rugosidade=0.72, brilho_tecido=0.12)
    nt = mat.node_tree
    n = nt.nodes
    ruido = n.new("ShaderNodeTexWave")
    ruido.wave_type = "BANDS"
    ruido.bands_direction = "Z"
    ruido.inputs["Scale"].default_value = escala_malha
    ruido.inputs["Distortion"].default_value = 2.0
    relevo = n.new("ShaderNodeBump")
    relevo.inputs["Strength"].default_value = 0.08
    relevo.inputs["Distance"].default_value = 0.0005
    nt.links.new(ruido.outputs["Fac"], relevo.inputs["Height"])
    nt.links.new(relevo.outputs["Normal"], n["Principled BSDF"].inputs["Normal"])
    return mat


def material_emissivo(nome, cor, forca):
    mat = bpy.data.materials.new(nome)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = (*cor, 1)
    bsdf.inputs["Emission Color"].default_value = (*cor, 1)
    bsdf.inputs["Emission Strength"].default_value = forca
    return mat


def criar_materiais():
    return {
        "piso": material_textura("Piso madeira", "laminate_floor_02", escala=1.0, tom=(0.86, 0.74, 0.6), rugosidade_mult=0.75),
        "cubo": material_textura("Cubo madeira", "oak_veneer_01", escala=1.0, tom=(1.0, 0.93, 0.84)),
        "ripado": material_textura("Ripado", "wood_table_001", escala=1.0, tom=(0.92, 0.74, 0.58), rugosidade_mult=0.9),
        "parede": material_basico("Parede", (0.83, 0.83, 0.81), rugosidade=0.92),
        "moldura": material_basico("Moldura greige", (0.46, 0.43, 0.39), rugosidade=0.75),
        "corredor": material_basico("Corredor do shopping", (0.72, 0.68, 0.62), rugosidade=0.18),
        "vidro": material_vidro(),
        "manequim": material_basico("Manequim cinza", (0.16, 0.16, 0.16), rugosidade=0.5),
        "manequim_preto": material_basico("Manequim preto", (0.03, 0.03, 0.03), rugosidade=0.45),
        "metal": material_basico("Base metálica", (0.55, 0.55, 0.55), rugosidade=0.32, metalico=1.0),
        "letreiro": material_emissivo("Letreiro", (1.0, 0.97, 0.92), 9.0),
        "spot": material_emissivo("Spot do teto", (1.0, 0.9, 0.75), 30.0),
        "casaco": material_tecido("Casaco PowerCool", (0.014, 0.017, 0.028)),
        "shorts": material_tecido("Shorts", (0.022, 0.03, 0.065), escala_malha=1400.0),
        "tenis": material_basico("Tênis", (0.82, 0.82, 0.8), rugosidade=0.6),
        "ziper": material_basico("Zíper", (0.02, 0.02, 0.02), rugosidade=0.3, metalico=0.6),
    }


# ---------------------------------------------------------------- manequim

# Esqueleto do manequim feminino abstrato (sem rosto, como os das lojas).
# Cada ponto: nome -> (x, y, z, raio_x, raio_y). Altura total ~1,76 m.
ESQUELETO = {
    "pe_e": (-0.105, -0.12, 0.035, 0.035, 0.028), "pe_d": (0.105, -0.12, 0.035, 0.035, 0.028),
    "tornozelo_e": (-0.095, 0.0, 0.08, 0.033, 0.034), "tornozelo_d": (0.095, 0.0, 0.08, 0.033, 0.034),
    "panturrilha_e": (-0.092, 0.01, 0.30, 0.047, 0.05), "panturrilha_d": (0.092, 0.01, 0.30, 0.047, 0.05),
    "joelho_e": (-0.088, -0.005, 0.48, 0.048, 0.05), "joelho_d": (0.088, -0.005, 0.48, 0.048, 0.05),
    "coxa_e": (-0.092, 0.0, 0.70, 0.075, 0.078), "coxa_d": (0.092, 0.0, 0.70, 0.075, 0.078),
    "quadril_e": (-0.092, 0.005, 0.86, 0.095, 0.095), "quadril_d": (0.092, 0.005, 0.86, 0.095, 0.095),
    "pelve": (0.0, 0.01, 0.92, 0.165, 0.105),
    "cintura": (0.0, 0.0, 1.06, 0.115, 0.08),
    "peito": (0.0, -0.012, 1.23, 0.135, 0.105),
    "ombros": (0.0, 0.0, 1.37, 0.125, 0.08),
    "pescoco_base": (0.0, 0.0, 1.44, 0.052, 0.05),
    "pescoco_topo": (0.0, 0.0, 1.52, 0.045, 0.045),
    "ombro_e": (-0.17, 0.0, 1.365, 0.048, 0.046), "ombro_d": (0.17, 0.0, 1.365, 0.048, 0.046),
    "cotovelo_e": (-0.235, 0.025, 1.11, 0.033, 0.033), "cotovelo_d": (0.235, 0.025, 1.11, 0.033, 0.033),
    "pulso_e": (-0.275, -0.005, 0.875, 0.024, 0.02), "pulso_d": (0.275, -0.005, 0.875, 0.024, 0.02),
    "mao_e": (-0.29, -0.01, 0.775, 0.028, 0.012), "mao_d": (0.29, -0.01, 0.775, 0.028, 0.012),
}
OSSOS = [
    ("pe_e", "tornozelo_e"), ("tornozelo_e", "panturrilha_e"), ("panturrilha_e", "joelho_e"), ("joelho_e", "coxa_e"), ("coxa_e", "quadril_e"), ("quadril_e", "pelve"),
    ("pe_d", "tornozelo_d"), ("tornozelo_d", "panturrilha_d"), ("panturrilha_d", "joelho_d"), ("joelho_d", "coxa_d"), ("coxa_d", "quadril_d"), ("quadril_d", "pelve"),
    ("pelve", "cintura"), ("cintura", "peito"), ("peito", "ombros"), ("ombros", "pescoco_base"), ("pescoco_base", "pescoco_topo"),
    ("ombros", "ombro_e"), ("ombro_e", "cotovelo_e"), ("cotovelo_e", "pulso_e"), ("pulso_e", "mao_e"),
    ("ombros", "ombro_d"), ("ombro_d", "cotovelo_d"), ("cotovelo_d", "pulso_d"), ("pulso_d", "mao_d"),
]


def criar_corpo_manequim():
    """Corpo liso a partir do esqueleto (modificadores Skin + Subdivision), já aplicado."""
    nomes = list(ESQUELETO)
    malha = bpy.data.meshes.new("Manequim")
    malha.from_pydata(
        [ESQUELETO[k][:3] for k in nomes],
        [(nomes.index(a), nomes.index(b)) for a, b in OSSOS],
        [],
    )
    obj = bpy.data.objects.new("Manequim", malha)
    bpy.context.collection.objects.link(obj)
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)

    pele = obj.modifiers.new("Skin", "SKIN")
    pele.use_smooth_shade = True
    raios = obj.data.skin_vertices[0].data
    for i, k in enumerate(nomes):
        raios[i].radius = ESQUELETO[k][3:]
        raios[i].use_root = k == "pelve"
    sub = obj.modifiers.new("Subdivision", "SUBSURF")
    sub.levels = 2
    sub.render_levels = 2

    deps = bpy.context.evaluated_depsgraph_get()
    pronto = bpy.data.meshes.new_from_object(obj.evaluated_get(deps))
    bpy.data.objects.remove(obj)
    corpo = bpy.data.objects.new("Manequim", pronto)
    bpy.context.collection.objects.link(corpo)

    # Cabeça em forma de ovo, levemente inclinada para a frente.
    bpy.ops.mesh.primitive_uv_sphere_add(segments=48, ring_count=24, location=(0, -0.008, 1.635))
    cabeca = bpy.context.active_object
    cabeca.scale = (0.072, 0.088, 0.112)
    cabeca.rotation_euler = (math.radians(-8), 0, 0)
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
    suavizar(cabeca)

    bpy.ops.object.select_all(action="DESELECT")
    corpo.select_set(True)
    cabeca.select_set(True)
    bpy.context.view_layer.objects.active = corpo
    bpy.ops.object.join()
    suavizar(corpo)
    return corpo


def recortar_roupa(corpo, nome, dentro, afastamento, material, espessura=0.003):
    """Cria uma peça justa copiando a parte do corpo onde `dentro(co)` é verdadeiro
    e afastando-a pela normal, como roupa esportiva de compressão."""
    malha = corpo.data.copy()
    bm = bmesh.new()
    bm.from_mesh(malha)
    bm.verts.ensure_lookup_table()
    fora = [v for v in bm.verts if not dentro(v.co)]
    bmesh.ops.delete(bm, geom=fora, context="VERTS")
    bm.normal_update()
    for v in bm.verts:
        v.co += v.normal * afastamento
    bm.to_mesh(malha)
    bm.free()
    malha.materials.clear()
    malha.materials.append(material)
    peca = bpy.data.objects.new(nome, malha)
    bpy.context.collection.objects.link(peca)
    solido = peca.modifiers.new("Espessura", "SOLIDIFY")
    solido.thickness = espessura
    solido.offset = 1
    suave = peca.modifiers.new("Suavizar", "SUBSURF")
    suave.levels = 1
    suave.render_levels = 1
    suavizar(peca)
    return peca


def vestir_casaco_e_shorts(corpo, mats):
    """Fase 2: roupa de teste no manequim da parada 1 (casaco justo com gola alta e bermuda)."""
    pecas = [
        recortar_roupa(corpo, "Casaco", lambda c: 0.84 <= c.z <= 1.535 and not (abs(c.x) > 0.2 and c.z < 0.87), 0.010, mats["casaco"]),
        recortar_roupa(corpo, "Shorts", lambda c: 0.60 <= c.z <= 0.95, 0.006, mats["shorts"]),
        recortar_roupa(corpo, "Tênis", lambda c: c.z <= 0.115, 0.014, mats["tenis"], espessura=0.01),
    ]
    # Zíper central do casaco.
    zip_ = caixa("Zíper", (0, -0.112, 1.18), (0.006, 0.004, 0.62), mats["ziper"])
    pecas.append(zip_)
    return pecas


def base_do_manequim(mats):
    base = caixa("Base", (0, 0, 0.006), (0.42, 0.42, 0.012), mats["metal"])
    haste = bpy.ops.mesh.primitive_cylinder_add(radius=0.008, depth=0.3, location=(0.09, 0.02, 0.16))
    haste = bpy.context.active_object
    haste.data.materials.append(mats["metal"])
    return [base, haste]


def agrupar(objs, local, rotacao_z=0.0):
    vazio = bpy.data.objects.new("Grupo", None)
    bpy.context.collection.objects.link(vazio)
    for o in objs:
        o.parent = vazio
    vazio.location = local
    vazio.rotation_euler = (0, 0, rotacao_z)
    return vazio


# ---------------------------------------------------------------- cenário

def montar_cenario(mats):
    largura = FIM_X - INICIO_X
    meio_x = (INICIO_X + FIM_X) / 2

    # Corredor do shopping (porcelanato claro) e piso da vitrine (madeira).
    plano("Corredor", (meio_x, -4.0, 0), (largura + 8, 8), material=mats["corredor"])
    caixa("Base da vitrine", (meio_x, -0.06, PISO_VITRINE / 2), (largura, 0.12, PISO_VITRINE), mats["moldura"])
    piso = plano("Piso", (meio_x, FUNDO_Y / 2, PISO_VITRINE), (largura, FUNDO_Y), material=mats["piso"])
    bpy.context.view_layer.objects.active = piso
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.uv.cube_project(cube_size=1.6)
    bpy.ops.object.mode_set(mode="OBJECT")

    # Parede do fundo com o logo em relevo, teto e laterais.
    caixa("Parede", (meio_x, FUNDO_Y + 0.05, TETO_Z / 2), (largura, 0.1, TETO_Z), mats["parede"])
    caixa("Teto", (meio_x, FUNDO_Y / 2, TETO_Z + 0.05), (largura, FUNDO_Y + 0.2, 0.1), mats["parede"])
    caixa("Rodapé", (meio_x, FUNDO_Y - 0.01, PISO_VITRINE + 0.04), (largura, 0.02, 0.08), mats["parede"])
    for i in range(0, len(PARADAS), 3):
        relevo_logo(i * ESPACO_PARADAS - 0.9, mats)

    # Spots embutidos no teto e luz de destaque em cada parada.
    for i in range(len(PARADAS)):
        x = i * ESPACO_PARADAS
        bpy.ops.mesh.primitive_cylinder_add(radius=0.045, depth=0.01, location=(x, 0.35, TETO_Z - 0.002))
        bpy.context.active_object.data.materials.append(mats["spot"])
        spot = bpy.data.lights.new(f"Spot {i + 1}", "SPOT")
        spot.energy = 120
        spot.color = LUZ_QUENTE
        spot.spot_size = math.radians(38)
        spot.spot_blend = 0.55
        spot.shadow_soft_size = 0.06
        obj = bpy.data.objects.new(f"Spot {i + 1}", spot)
        bpy.context.collection.objects.link(obj)
        obj.location = (x, 0.35, TETO_Z - 0.03)
        alvo = Vector((x, 1.15, 1.15))
        obj.rotation_euler = (alvo - obj.location).to_track_quat("-Z", "Y").to_euler()

        # Facho na parede do fundo, entre as paradas (o "scallop" de luz das vitrines).
        if i < len(PARADAS) - 1:
            facho = bpy.data.lights.new(f"Facho {i + 1}", "SPOT")
            facho.energy = 220
            facho.color = LUZ_QUENTE
            facho.spot_size = math.radians(60)
            facho.spot_blend = 0.35
            facho.shadow_soft_size = 0.02
            obj = bpy.data.objects.new(f"Facho {i + 1}", facho)
            bpy.context.collection.objects.link(obj)
            obj.location = (x + ESPACO_PARADAS / 2, FUNDO_Y - 0.35, TETO_Z - 0.03)
            alvo = Vector((x + ESPACO_PARADAS / 2, FUNDO_Y, 0.6))
            obj.rotation_euler = (alvo - obj.location).to_track_quat("-Z", "Y").to_euler()

    # Luz difusa na parede do fundo (sanca).
    sanca = bpy.data.lights.new("Sanca", "AREA")
    sanca.shape = "RECTANGLE"
    sanca.size = largura
    sanca.size_y = 0.15
    sanca.energy = 500
    sanca.color = LUZ_QUENTE
    obj = bpy.data.objects.new("Sanca", sanca)
    bpy.context.collection.objects.link(obj)
    obj.location = (meio_x, FUNDO_Y - 0.25, TETO_Z - 0.05)
    obj.rotation_euler = (math.radians(-35), 0, 0)

    # Luz geral suave do interior.
    geral = bpy.data.lights.new("Geral", "AREA")
    geral.shape = "RECTANGLE"
    geral.size = largura
    geral.size_y = 1.2
    geral.energy = 260
    geral.color = (1.0, 0.92, 0.82)
    obj = bpy.data.objects.new("Geral", geral)
    bpy.context.collection.objects.link(obj)
    obj.location = (meio_x, 1.0, TETO_Z - 0.02)

    # Vidro contínuo (sem caixilhos, como nas lojas novas) e pilares cinza nas pontas.
    for px in (INICIO_X + 0.15, FIM_X - 0.15):
        caixa("Pilar", (px, -0.12, (TETO_Z + PISO_VITRINE) / 2), (0.3, 0.24, TETO_Z), mats["moldura"])
    caixa("Vidro", (meio_x, 0.0, (TETO_Z + PISO_VITRINE) / 2), (largura - 0.6, 0.01, TETO_Z - PISO_VITRINE), mats["vidro"])

    # Fachada: faixa cinza e ripado de madeira com o letreiro.
    caixa("Faixa", (meio_x, -0.12, TETO_Z + 0.08), (largura, 0.24, 0.16), mats["moldura"])
    montar_ripado(meio_x, largura, mats)
    letreiro(FIM_X - 2.6, mats)

    # Reflexos: luminárias do corredor do shopping atrás da câmera.
    for k in range(6):
        plano("Luminária do corredor", (INICIO_X + k * 2.6, -3.2, 3.6), (1.6, 0.12), material=mats["letreiro"])


def montar_ripado(meio_x, largura, mats):
    malha_ripa = None
    n = int(largura / 0.055)
    altura = FACHADA_TOPO - (TETO_Z + 0.16)
    z = TETO_Z + 0.16 + altura / 2
    ripas = []
    for i in range(n):
        x = INICIO_X + 0.03 + i * 0.055
        r = caixa("Ripa", (x, -0.2, z), (0.04, 0.03, altura), mats["ripado"])
        ripas.append(r)
    caixa("Fundo do ripado", (meio_x, -0.17, z), (largura, 0.02, altura), mats["moldura"])
    bpy.ops.object.select_all(action="DESELECT")
    for r in ripas:
        r.select_set(True)
    bpy.context.view_layer.objects.active = ripas[0]
    bpy.ops.object.join()
    ripado = bpy.context.active_object
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.uv.cube_project(cube_size=1.2)
    bpy.ops.object.mode_set(mode="OBJECT")
    return ripado


def texto(conteudo, tamanho, extrusao, material):
    curva = bpy.data.curves.new("Texto", "FONT")
    curva.body = conteudo
    if os.path.exists(FONTE):
        curva.font = bpy.data.fonts.load(FONTE, check_existing=True)
    curva.size = tamanho
    curva.extrude = extrusao
    curva.align_x = "CENTER"
    curva.align_y = "CENTER"
    obj = bpy.data.objects.new("Texto", curva)
    bpy.context.collection.objects.link(obj)
    obj.data.materials.append(material)
    return obj


def letreiro(x, mats):
    obj = texto("Track&Field", 0.42, 0.02, mats["letreiro"])
    obj.location = (x, -0.25, (TETO_Z + 0.16 + FACHADA_TOPO) / 2)
    obj.rotation_euler = (math.radians(90), 0, 0)
    luz = bpy.data.lights.new("Brilho do letreiro", "AREA")
    luz.size = 2.4
    luz.size_y = 0.4
    luz.energy = 120
    o = bpy.data.objects.new("Brilho do letreiro", luz)
    bpy.context.collection.objects.link(o)
    o.location = (x, -0.35, obj.location.z)
    o.rotation_euler = (math.radians(-90), 0, 0)


def relevo_logo(x, mats):
    obj = texto("Track&Field", 0.34, 0.008, mats["parede"])
    obj.location = (x, FUNDO_Y - 0.01, 2.5)
    obj.rotation_euler = (math.radians(90), 0, 0)


def montar_paradas(mats):
    corpo_base = criar_corpo_manequim()
    corpo_base.data.materials.append(mats["manequim"])
    for i, parada in enumerate(PARADAS):
        x = i * ESPACO_PARADAS
        if parada["tipo"] == "cubo":
            lado = 0.5
            cubo = caixa(f"Cubo {i + 1}", (x, 1.15, PISO_VITRINE + lado / 2), (lado * 1.1, lado, lado), mats["cubo"])
            bpy.context.view_layer.objects.active = cubo
            bpy.ops.object.mode_set(mode="EDIT")
            bpy.ops.uv.cube_project(cube_size=1.0)
            bpy.ops.object.mode_set(mode="OBJECT")
            biselar(cubo, 0.004)
            continue
        corpo = corpo_base.copy()
        corpo.data = corpo_base.data.copy()
        bpy.context.collection.objects.link(corpo)
        if i % 2 == 1:
            corpo.data.materials[0] = mats["manequim_preto"]
        objs = [corpo] + base_do_manequim(mats)
        if i == 0:
            objs += vestir_casaco_e_shorts(corpo, mats)
        giro = math.radians([-12, 0, 10, -6, 14, 0, -10, 0][i])
        agrupar(objs, (x, 1.15, PISO_VITRINE + 0.012), giro)
    bpy.data.objects.remove(corpo_base)


def biselar(obj, largura):
    mod = obj.modifiers.new("Bisel", "BEVEL")
    mod.width = largura
    mod.segments = 2


# ---------------------------------------------------------------- câmera e render

def posicionar_camera(parada):
    """Câmera fora da vitrine, à altura do peito, com o produto à direita do centro
    (no computador o letreiro do link fica à esquerda; no celular a imagem é recortada
    em volta do produto)."""
    cam_dados = bpy.data.cameras.new("Câmera")
    cam_dados.lens = 32
    cam_dados.sensor_width = 36
    cam = bpy.data.objects.new("Câmera", cam_dados)
    bpy.context.collection.objects.link(cam)
    x = parada * ESPACO_PARADAS
    cam.location = (x - 0.6, -2.4, 1.1)
    cam.rotation_euler = (math.radians(90), 0, 0)
    cam_dados.shift_y = -0.02
    bpy.context.scene.camera = cam
    return cam


def configurar_render(largura, altura, amostras, saida):
    cena = bpy.context.scene
    cena.render.engine = "CYCLES"
    cena.cycles.device = "CPU"
    cena.cycles.samples = amostras
    cena.cycles.use_adaptive_sampling = True
    cena.cycles.adaptive_threshold = 0.02
    cena.cycles.use_denoising = True
    cena.cycles.max_bounces = 8
    cena.cycles.diffuse_bounces = 4
    cena.cycles.glossy_bounces = 4
    cena.cycles.transparent_max_bounces = 16
    cena.render.resolution_x = largura
    cena.render.resolution_y = altura
    cena.render.film_transparent = False
    cena.view_settings.view_transform = "AgX"
    cena.view_settings.look = "AgX - Medium High Contrast"
    cena.view_settings.exposure = 0.0
    cena.render.image_settings.file_format = "PNG"
    cena.render.filepath = saida

    mundo = bpy.data.worlds.new("Shopping")
    mundo.use_nodes = True
    fundo = mundo.node_tree.nodes["Background"]
    fundo.inputs["Color"].default_value = (0.55, 0.52, 0.48, 1)
    fundo.inputs["Strength"].default_value = 0.35
    cena.world = mundo


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
    p = argparse.ArgumentParser(description="Render da vitrine Track&Field")
    p.add_argument("--parada", type=int, default=0, help="Índice da parada (0 a 7)")
    p.add_argument("--largura", type=int, default=1600)
    p.add_argument("--altura", type=int, default=1200)
    p.add_argument("--amostras", type=int, default=256)
    p.add_argument("--previa", action="store_true", help="480x360 com 24 amostras")
    p.add_argument("--saida", default=os.path.join(PASTA, "renders", "parada-{parada}.png"))
    p.add_argument("--blend", help="Salva também o arquivo .blend neste caminho")
    a = p.parse_args(argv)
    if a.previa:
        a.largura, a.altura, a.amostras = 480, 360, 24
    saida = os.path.abspath(a.saida.format(parada=a.parada))
    os.makedirs(os.path.dirname(saida), exist_ok=True)

    limpar_cena()
    mats = criar_materiais()
    montar_cenario(mats)
    montar_paradas(mats)
    posicionar_camera(a.parada)
    configurar_render(a.largura, a.altura, a.amostras, saida)
    if a.blend:
        bpy.ops.wm.save_as_mainfile(filepath=os.path.abspath(a.blend))
    bpy.ops.render.render(write_still=True)
    print("Render salvo em", saida)


if __name__ == "__main__":
    main()
