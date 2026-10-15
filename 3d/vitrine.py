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

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import produtos  # noqa: E402

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


def material_emissivo(nome, cor, forca):
    mat = bpy.data.materials.new(nome)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = (*cor, 1)
    bsdf.inputs["Emission Color"].default_value = (*cor, 1)
    bsdf.inputs["Emission Strength"].default_value = forca
    return mat


def criar_materiais():
    return produtos.criar_materiais() | {
        "piso": material_textura("Piso madeira", "laminate_floor_02", escala=1.0, tom=(0.86, 0.74, 0.6), rugosidade_mult=0.75),
        "cubo": material_textura("Cubo madeira", "oak_veneer_01", escala=1.0, tom=(1.0, 0.93, 0.84)),
        "ripado": material_textura("Ripado", "wood_table_001", escala=1.0, tom=(0.92, 0.74, 0.58), rugosidade_mult=0.9),
        "parede": material_basico("Parede", (0.83, 0.83, 0.81), rugosidade=0.92),
        "moldura": material_basico("Moldura greige", (0.46, 0.43, 0.39), rugosidade=0.75),
        "corredor": material_basico("Corredor do shopping", (0.72, 0.68, 0.62), rugosidade=0.18),
        "vidro": material_vidro(),
        "metal": material_basico("Base metálica", (0.55, 0.55, 0.55), rugosidade=0.32, metalico=1.0),
        "letreiro": material_emissivo("Letreiro", (1.0, 0.97, 0.92), 9.0),
        "spot": material_emissivo("Spot do teto", (1.0, 0.9, 0.75), 30.0),
    }


# ---------------------------------------------------------------- paradas

def base_do_manequim(mats):
    base = caixa("Base", (0, 0, 0.006), (0.42, 0.42, 0.012), mats["metal"])
    biselar(base, 0.003)
    return [base]


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
    for i, parada in enumerate(PARADAS):
        x = i * ESPACO_PARADAS
        objs, pedestal = produtos.montar_produto(parada["produto"], mats)
        if pedestal is None:
            giro = math.radians([-10, 0, 8, -6, 10, 0, -8, 0][i])
            agrupar(objs + base_do_manequim(mats), (x, 1.15, PISO_VITRINE + 0.012), giro)
            continue
        cubo = caixa(f"Cubo {i + 1}", (x, 1.15, PISO_VITRINE + pedestal / 2), (0.56, 0.46, pedestal), mats["cubo"])
        bpy.context.view_layer.objects.active = cubo
        bpy.ops.object.mode_set(mode="EDIT")
        bpy.ops.uv.cube_project(cube_size=1.0)
        bpy.ops.object.mode_set(mode="OBJECT")
        biselar(cubo, 0.004)
        agrupar(objs, (x, 1.12, PISO_VITRINE + pedestal), math.radians(produtos.SOBRE_CUBO[parada["produto"]][4]))


def biselar(obj, largura):
    mod = obj.modifiers.new("Bisel", "BEVEL")
    mod.width = largura
    mod.segments = 2


# ---------------------------------------------------------------- câmera e render

def enquadramento(parada):
    """Posição e lente da câmera de uma parada: (local, lente).
    Manequim: inteiro no quadro. Cubo: mais perto, na altura do produto."""
    x = parada * ESPACO_PARADAS
    if PARADAS[parada]["tipo"] == "cubo":
        _, pedestal, lente, altura, _ = produtos.SOBRE_CUBO[PARADAS[parada]["produto"]]
        distancia = 2.4 + 1.12
        meia_largura = distancia * 18 / lente
        return (x - 0.3 * meia_largura, -2.4, PISO_VITRINE + pedestal + altura * 0.45), lente
    return (x - 0.6, -2.4, 1.1), 32


def posicionar_camera(parada):
    """Câmera fora da vitrine, sem inclinação (verticais retas), com o produto à direita
    do centro: no computador o letreiro do link fica à esquerda; no celular a imagem é
    recortada em volta do produto."""
    cam_dados = bpy.data.cameras.new("Câmera")
    cam_dados.sensor_width = 36
    cam = bpy.data.objects.new("Câmera", cam_dados)
    bpy.context.collection.objects.link(cam)
    local, lente = enquadramento(parada)
    cam.location = local
    cam_dados.lens = lente
    cam.rotation_euler = (math.radians(90), 0, 0)
    cam_dados.shift_y = -0.02
    bpy.context.scene.camera = cam
    return cam


def suavizar_tempo(t):
    """Aceleração e frenagem suaves (smootherstep), como um travelling de câmera."""
    return t * t * t * (t * (6 * t - 15) + 10)


def animar_transicao(origem, quadros):
    """Anima a câmera da parada `origem` até a seguinte em `quadros` quadros.
    O primeiro e o último quadro são exatamente os enquadramentos das duas paradas.
    A lente é interpolada pelo ângulo de visão, para o zoom parecer uniforme."""
    cam = posicionar_camera(origem)
    (l0, f0), (l1, f1) = enquadramento(origem), enquadramento(origem + 1)
    ang0, ang1 = 2 * math.atan(18 / f0), 2 * math.atan(18 / f1)
    for q in range(quadros):
        t = suavizar_tempo(q / (quadros - 1))
        cam.location = Vector(l0).lerp(Vector(l1), t)
        cam.data.lens = 18 / math.tan((ang0 + (ang1 - ang0) * t) / 2)
        cam.keyframe_insert("location", frame=q + 1)
        cam.data.keyframe_insert("lens", frame=q + 1)
    cena = bpy.context.scene
    cena.frame_start, cena.frame_end = 1, quadros
    cena.render.fps = 24
    # Desfoque de movimento leve: deixa o travelling natural e esconde o ruído das poucas amostras.
    cena.render.use_motion_blur = os.environ.get("DESFOQUE", "1") == "1"
    cena.render.motion_blur_shutter = 0.5
    cena.render.use_persistent_data = True
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
    p.add_argument("--transicao", action="store_true",
                   help="Renderiza os quadros do travelling da parada --parada até a seguinte; "
                        "--saida vira a pasta dos quadros")
    p.add_argument("--quadros", type=int, default=24, help="Quadros da transição (24 por segundo)")
    p.add_argument("--apenas-quadro", type=int, help="Renderiza só este quadro da transição (para testar)")
    p.add_argument("--so-pares", action="store_true",
                   help="Renderiza só os quadros pares da transição (2, 4, ...). Com --quadros 23, completa "
                        "uma transição já feita com 12 quadros, que correspondem aos ímpares")
    a = p.parse_args(argv)
    if a.previa:
        a.largura, a.altura, a.amostras = 480, 360, 24
    saida = os.path.abspath(a.saida.format(parada=a.parada))
    os.makedirs(saida if a.transicao else os.path.dirname(saida), exist_ok=True)

    limpar_cena()
    mats = criar_materiais()
    montar_cenario(mats)
    montar_paradas(mats)
    if a.transicao:
        if not 0 <= a.parada < len(PARADAS) - 1:
            sys.exit("A transição vai da parada --parada até a seguinte: use 0 a %d." % (len(PARADAS) - 2))
        animar_transicao(a.parada, a.quadros)
        configurar_render(a.largura, a.altura, a.amostras, os.path.join(saida, "quadro-####"))
    else:
        posicionar_camera(a.parada)
        configurar_render(a.largura, a.altura, a.amostras, saida)
    if a.blend:
        bpy.ops.wm.save_as_mainfile(filepath=os.path.abspath(a.blend))
    if a.transicao and a.apenas_quadro:
        cena = bpy.context.scene
        cena.frame_start = cena.frame_end = a.apenas_quadro
    elif a.transicao and a.so_pares:
        cena = bpy.context.scene
        cena.frame_start, cena.frame_end, cena.frame_step = 2, a.quadros - 1, 2
    if a.transicao:
        bpy.ops.render.render(animation=True)
        print("Quadros salvos em", saida)
    else:
        bpy.ops.render.render(write_still=True)
        print("Render salvo em", saida)


if __name__ == "__main__":
    main()
