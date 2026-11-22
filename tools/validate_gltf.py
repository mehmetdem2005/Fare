#!/usr/bin/env python3
"""Validate glTF 2.0 GLB skin inverse bind matrices against the node rest transforms."""
import json, math, struct, sys
from pathlib import Path
import numpy as np

def read_glb(path):
    data = Path(path).read_bytes()
    if data[:4] != b'glTF':
        raise ValueError('Not a GLB')
    pos = 12
    chunks = []
    while pos < len(data):
        length, kind = struct.unpack_from('<I4s', data, pos)
        chunks.append((kind, data[pos+8:pos+8+length]))
        pos += 8+length
    gltf = json.loads(next(body for kind,body in chunks if kind == b'JSON'))
    raw = next(body for kind,body in chunks if kind == b'BIN\x00')
    return gltf, raw

def matrix(node):
    if 'matrix' in node:
        return np.array(node['matrix'],dtype=float).reshape(4,4).T
    p = np.array(node.get('translation',[0,0,0]),dtype=float)
    q = node.get('rotation',[0,0,0,1]); x,y,z,w=q
    r=np.array([
       [1-2*(y*y+z*z), 2*(x*y-z*w), 2*(x*z+y*w)],
       [2*(x*y+z*w), 1-2*(x*x+z*z), 2*(y*z-x*w)],
       [2*(x*z-y*w), 2*(y*z+x*w), 1-2*(x*x+y*y)]])
    t=np.eye(4);t[:3,:3]=r @ np.diag(node.get('scale',[1,1,1]));t[:3,3]=p
    return t

def accessor(j,raw,index,width):
    a=j['accessors'][index];v=j['bufferViews'][a['bufferView']]
    if a['componentType']!=5126:raise ValueError('Expected float accessor')
    stride=v.get('byteStride',width*4)
    offset=v.get('byteOffset',0)+a.get('byteOffset',0)
    return np.stack([np.frombuffer(raw,dtype='<f4',count=width,offset=offset+k*stride) for k in range(a['count'])])

def validate(path):
    j,raw=read_glb(path)
    nodes=j['nodes'];parents={}
    for k,node in enumerate(nodes):
        for kid in node.get('children',[]):parents[kid]=k
    globals_={}
    def glob(i):
        if i not in globals_:
            m=matrix(nodes[i]);globals_[i]=glob(parents[i]) @ m if i in parents else m
        return globals_[i]
    print('MODEL',path,'nodes=',len(nodes),'skins=',len(j.get('skins',[])))
    if not j.get('skins'):raise ValueError('No skin in GLB')
    for i,skin in enumerate(j['skins']):
        joints=skin['joints']
        inverse=accessor(j,raw,skin['inverseBindMatrices'],16)
        if len(joints)!=len(inverse):raise ValueError('Joint/IBM count mismatch')
        errors=[]
        for node_idx in [k for k,n in enumerate(nodes) if n.get('skin') == i]:
            mesh_inv=np.linalg.inv(glob(node_idx))
            for joint,flat in zip(joints,inverse):
                ibm=flat.reshape(4,4).T
                bind=mesh_inv @ glob(joint) @ ibm
                errors.append(np.max(np.abs(bind-np.eye(4))))
        max_error=max(errors) if errors else 100.0
        print('SKIN',i,'JOINTS',len(joints),'MAX_BIND_ERROR',max_error)
        if max_error > 0.05:raise ValueError('Rest pose skin matrices do not match skeleton: '+str(max_error))
    for mesh in j.get('meshes',[]):
        for prim in mesh['primitives']:
            if 'TEXCOORD_0' not in prim['attributes']:raise ValueError('Missing mouse UV')
            uv=accessor(j,raw,prim['attributes']['TEXCOORD_0'],2)
            if not np.isfinite(uv).all():raise ValueError('Nonfinite UV coordinates')
            print('UV_RANGE',uv.min(axis=0).tolist(),uv.max(axis=0).tolist())
    print('GLB_SKIN_UV_VALIDATION_OK')

if __name__=='__main__':
    try:validate(sys.argv[1])
    except Exception as exc:
        print('GLB_SKIN_UV_VALIDATION_FAILED',repr(exc))
        sys.exit(1)
