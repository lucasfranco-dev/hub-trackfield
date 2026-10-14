"""
Gera os manequins da vitrine (feminino e masculino) a partir do corpo base do
MakeHuman, pelo add-on MPFB 2 (CC0), e salva em 3d/modelos/*.glb.

O corpo recebe proporções de manequim de loja, braços relaxados ao lado do corpo
e a cabeça trocada por uma forma lisa de ovo, sem rosto, como nas lojas.

Uso:
    python 3d/gerar_manequins.py --mpfb caminho/para/add-on-mpfb-v2.0.18.zip

O zip do MPFB vem de https://extensions.blender.org/add-ons/mpfb/ e só é
necessário para gerar os modelos; a vitrine usa os .glb prontos.
"""

import argparse
import math
import os
import sys

import bpy  # precisa vir antes de bmesh e mathutils
import bmesh
from mathutils import Matrix, Quaternion, Vector

PASTA = os.path.dirname(os.path.abspath(__file__))
SAIDA = os.path.join(PASTA, "modelos")

MANEQUINS = {
    "manequim-feminino": {
        "macro": {"gender": 0.0, "age": 0.45, "muscle": 0.62, "weight": 0.38, "proportions": 1.0,
                  "height": 0.75, "cupsize": 0.35, "firmness": 0.85,
                  "race": {"asian": 0.33, "caucasian": 0.34, "african": 0.33}},
        "braco": 17, "antebraco": 14,
    },
    "manequim-masculino": {
        "macro": {"gender": 1.0, "age": 0.45, "muscle": 0.56, "weight": 0.4, "proportions": 1.0,
                  "height": 0.7, "cupsize": 0.5, "firmness": 0.5,
                  "race": {"asian": 0.33, "caucasian": 0.34, "african": 0.33}},
        "braco": 16, "antebraco": 12,
    },
}


# Regiões do corpo gravadas em cada vértice (atributo "_regiao") para recortar as roupas.
# "_t" é a posição do vértice ao longo do osso dominante: 0 na base, 1 na ponta.
REGIOES = {
    "pelvis": 0, "spine_01": 1, "spine_02": 2, "spine_03": 2, "clavicle": 3, "upperarm": 4, "lowerarm": 5,
    "hand": 6, "thumb": 6, "index": 6, "middle": 6, "ring": 6, "pinky": 6,
    "thigh": 7, "calf": 8, "foot": 9, "ball": 9, "neck_01": 10, "head": 11,
}
REGIAO_CABECA = 11


def regiao_do_osso(nome):
    base = nome.rsplit("_", 1)[0] if nome.endswith(("_l", "_r")) else nome
    base = base.split("_0")[0] if base.split("_0")[0] in REGIOES else base
    return REGIOES.get(base, REGIOES.get(nome, 1))


def marcar_regioes(corpo, armacao):
    """Grava em cada vértice a região do osso que mais o influencia e a posição ao longo
    dele, antes de aplicar a pose (os ossos ainda estão na posição de descanso)."""
    deslocamento = deslocamento_do_esqueleto(corpo, armacao)
    nomes = {g.index: g.name for g in corpo.vertex_groups}
    regiao = corpo.data.attributes.new("_regiao", "INT", "POINT")
    posicao = corpo.data.attributes.new("_t", "FLOAT", "POINT")
    # Avalia só com as formas (shape keys) aplicadas: a máscara mudaria a contagem de vértices.
    for mod in corpo.modifiers:
        mod.show_viewport = False
    deps = bpy.context.evaluated_depsgraph_get()
    avaliado = corpo.evaluated_get(deps).to_mesh()
    assert len(avaliado.vertices) == len(corpo.data.vertices)
    for v, va in zip(corpo.data.vertices, avaliado.vertices):
        pesos = [(g.weight, nomes[g.group]) for g in v.groups if nomes[g.group] in armacao.pose.bones]
        if not pesos:
            regiao.data[v.index].value = 1
            continue
        _, osso = max(pesos)
        pb = armacao.pose.bones[osso]
        cabeca = armacao.matrix_world @ pb.head + deslocamento
        cauda = armacao.matrix_world @ pb.tail + deslocamento
        eixo = cauda - cabeca
        t = (corpo.matrix_world @ va.co - cabeca).dot(eixo) / max(eixo.length_squared, 1e-9)
        regiao.data[v.index].value = regiao_do_osso(osso)
        posicao.data[v.index].value = max(0.0, min(1.0, t))
    corpo.evaluated_get(deps).to_mesh_clear()
    for mod in corpo.modifiers:
        mod.show_viewport = True


def instalar_mpfb(zip_mpfb):
    if "bl_ext.user_default.mpfb" not in sys.modules:
        bpy.ops.extensions.package_install_files(filepath=zip_mpfb, repo="user_default", enable_on_install=True)
    from bl_ext.user_default.mpfb.services.humanservice import HumanService
    return HumanService


def aplicar_modificadores(obj):
    bpy.context.view_layer.objects.active = obj
    for mod in list(obj.modifiers):
        bpy.ops.object.modifier_apply(modifier=mod.name)


def girar_osso_no_mundo(armacao, osso, rotacao, deslocamento):
    """Gira um osso em torno da articulação real do corpo usando uma rotação no espaço
    do mundo. `deslocamento` corrige a diferença entre o esqueleto e o corpo: com
    feet_on_ground o MPFB sobe o corpo, mas não o esqueleto. Como a deformação só
    depende da matriz do osso, girar em torno do ponto certo basta."""
    mw = armacao.matrix_world
    atual = mw @ osso.matrix
    pivo = atual.translation + deslocamento
    novo = Matrix.Translation(pivo) @ rotacao.to_matrix().to_4x4() @ Matrix.Translation(-pivo) @ atual
    osso.matrix = mw.inverted() @ novo
    bpy.context.view_layer.update()


def direcao_do_osso(armacao, osso):
    mw = armacao.matrix_world
    return ((mw @ osso.tail) - (mw @ osso.head)).normalized()


def deslocamento_do_esqueleto(corpo, armacao, osso="upperarm_l"):
    """Diferença entre onde o osso deveria estar no corpo e onde o esqueleto o colocou:
    centro dos vértices dominados pelo osso menos o meio do osso."""
    indice = corpo.vertex_groups[osso].index
    pontos = [corpo.matrix_world @ v.co for v in corpo.data.vertices
              if any(g.group == indice and g.weight > 0.9 for g in v.groups)]
    centro = sum(pontos, Vector()) / len(pontos)
    pb = armacao.pose.bones[osso]
    meio = armacao.matrix_world @ ((pb.head + pb.tail) / 2)
    return centro - meio


def posar_bracos(corpo, armacao, graus_abertura, graus_antebraco):
    """Baixa os braços da pose em A para junto do corpo, levemente afastados,
    com o cotovelo um pouco dobrado para a frente. O manequim olha para -Y."""
    deslocamento = deslocamento_do_esqueleto(corpo, armacao)
    print(f"deslocamento do esqueleto: {tuple(round(c, 3) for c in deslocamento)}")
    bpy.context.view_layer.objects.active = armacao
    bpy.ops.object.mode_set(mode="POSE")
    for lado, sinal in (("l", 1), ("r", -1)):
        braco = armacao.pose.bones[f"upperarm_{lado}"]
        alvo = Vector((sinal * math.sin(math.radians(graus_abertura)), 0.02, -math.cos(math.radians(graus_abertura)))).normalized()
        # A clavícula leva uma parte do giro, para o ombro não ficar quadrado.
        giro = direcao_do_osso(armacao, braco).rotation_difference(alvo)
        clavicula = armacao.pose.bones[f"clavicle_{lado}"]
        girar_osso_no_mundo(armacao, clavicula, Quaternion().slerp(giro, 0.35), deslocamento)
        girar_osso_no_mundo(armacao, braco, direcao_do_osso(armacao, braco).rotation_difference(alvo), deslocamento)
        antebraco = armacao.pose.bones[f"lowerarm_{lado}"]
        atual = direcao_do_osso(armacao, antebraco)
        alvo = Vector((atual.x * 0.6, -math.sin(math.radians(graus_antebraco)), atual.z)).normalized()
        girar_osso_no_mundo(armacao, antebraco, atual.rotation_difference(alvo), deslocamento)
    bpy.ops.object.mode_set(mode="OBJECT")


def cabeca_de_ovo(obj):
    """Corta a cabeça do corpo na altura do queixo e põe no lugar uma cabeça lisa em
    forma de ovo, sem rosto, como a dos manequins das lojas. O pescoço termina dentro
    do ovo, então o corte não aparece."""
    malha = obj.data
    zs = [v.co.z for v in malha.vertices]
    topo, altura = max(zs), max(zs) - min(zs)
    corte = topo - altura * 0.128
    cabeca = [v.co.copy() for v in malha.vertices if v.co.z > corte - altura * 0.02 and abs(v.co.x) < altura * 0.08]
    xs = [c.x for c in cabeca]
    ys = [c.y for c in cabeca]
    centro = Vector(((max(xs) + min(xs)) / 2, (max(ys) + min(ys)) / 2 - altura * 0.004, topo - altura * 0.066))

    bm = bmesh.new()
    bm.from_mesh(malha)
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if v.co.z > corte], context="VERTS")
    # Prolonga a ponta do pescoço para dentro do ovo.
    for v in bm.verts:
        if v.is_boundary and v.co.z > corte - altura * 0.02:
            v.co.z += altura * 0.03
    bm.to_mesh(malha)
    bm.free()

    # Esfera feita de quadrados (cubo subdividido e inflado), sem polos: a esfera UV
    # tem vértices com 64 arestas, que fazem a subdivisão gastar gigabytes de memória.
    bpy.ops.mesh.primitive_cube_add(size=2, location=(0, 0, 0))
    ovo = bpy.context.active_object
    bm = bmesh.new()
    bm.from_mesh(ovo.data)
    bmesh.ops.subdivide_edges(bm, edges=bm.edges[:], cuts=10, use_grid_fill=True)
    for v in bm.verts:
        v.co = v.co.normalized()
    bm.to_mesh(ovo.data)
    bm.free()
    for p in ovo.data.polygons:
        p.use_smooth = True
    ovo.location = centro
    ovo.scale = (altura * 0.04, altura * 0.049, altura * 0.064)
    ovo.rotation_euler = (math.radians(-10), 0, 0)
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    # Afina o queixo: a metade de baixo do ovo fica um pouco mais estreita.
    for v in ovo.data.vertices:
        if v.co.z < centro.z:
            f = 1 - 0.18 * min((centro.z - v.co.z) / (altura * 0.064), 1)
            v.co.x = centro.x + (v.co.x - centro.x) * f
            v.co.y = centro.y + (v.co.y - centro.y) * (0.5 + 0.5 * f)

    ovo.data.attributes.new("_regiao", "INT", "POINT")
    for item in ovo.data.attributes["_regiao"].data:
        item.value = REGIAO_CABECA
    ovo.data.attributes.new("_t", "FLOAT", "POINT")

    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    ovo.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.join()


def gerar(HumanService, nome, cfg):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    corpo = HumanService.create_human(mask_helpers=True, detailed_helpers=False, extra_vertex_groups=True,
                                      feet_on_ground=True, scale=0.1, macro_detail_dict=cfg["macro"])
    armacao = HumanService.add_builtin_rig(corpo, "game_engine", import_weights=True)
    for mod in corpo.modifiers:
        if mod.type == "ARMATURE":
            mod.use_deform_preserve_volume = True
    marcar_regioes(corpo, armacao)
    posar_bracos(corpo, armacao, cfg["braco"], cfg["antebraco"])

    bpy.ops.object.select_all(action="DESELECT")
    corpo.select_set(True)
    bpy.context.view_layer.objects.active = corpo
    if corpo.data.shape_keys:
        bpy.ops.object.shape_key_add(from_mix=True)
        for chave in list(corpo.data.shape_keys.key_blocks)[:-1]:
            corpo.shape_key_remove(chave)
        corpo.shape_key_remove(corpo.data.shape_keys.key_blocks[0])
    aplicar_modificadores(corpo)
    corpo.parent = None
    bpy.data.objects.remove(armacao)

    # Remove vértices soltos que sobram da geometria auxiliar (olhos, dentes, cílios).
    bm = bmesh.new()
    bm.from_mesh(corpo.data)
    soltos = [v for v in bm.verts if not v.link_faces]
    bmesh.ops.delete(bm, geom=soltos, context="VERTS")
    bm.to_mesh(corpo.data)
    bm.free()

    corpo.vertex_groups.clear()
    cabeca_de_ovo(corpo)
    for p in corpo.data.polygons:
        p.use_smooth = True
    corpo.name = nome
    corpo.data.materials.clear()

    os.makedirs(SAIDA, exist_ok=True)
    destino = os.path.join(SAIDA, nome + ".glb")
    bpy.ops.object.select_all(action="DESELECT")
    corpo.select_set(True)
    bpy.ops.export_scene.gltf(filepath=destino, use_selection=True, export_apply=True,
                              export_materials="NONE", export_yup=True, export_attributes=True)
    zs = [v.co.z for v in corpo.data.vertices]
    print(f"{destino}: {len(corpo.data.vertices)} vértices, altura {max(zs) - min(zs):.2f} m")


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
    p = argparse.ArgumentParser(description="Gera os manequins da vitrine com o MPFB")
    p.add_argument("--mpfb", required=True, help="Caminho do zip do add-on MPFB 2")
    p.add_argument("--apenas", choices=list(MANEQUINS), help="Gera só um dos manequins")
    a = p.parse_args(argv)
    HumanService = instalar_mpfb(os.path.abspath(a.mpfb))
    for nome, cfg in MANEQUINS.items():
        if a.apenas and nome != a.apenas:
            continue
        gerar(HumanService, nome, cfg)


if __name__ == "__main__":
    main()
