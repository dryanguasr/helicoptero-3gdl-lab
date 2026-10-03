import * as THREE from 'three';

/** Physical right-hand angles; internal elevation is opposite to course beta. */
export function orientRig(model:{yaw:THREE.Group;pitch:THREE.Group;roll:THREE.Group},x:number[]) {
  model.yaw.rotation.z=x[4];model.pitch.rotation.y=-x[0];model.roll.rotation.x=x[2];
}

/** Procedural teaching rig: shared low-poly geometry, no model/texture downloads. */
export function createBench(scene: THREE.Scene) {
  const box = new THREE.BoxGeometry(1,1,1);
  const cylinder = new THREE.CylinderGeometry(1,1,1,16);
  const guard = new THREE.TorusGeometry(.19,.008,5,32);
  const materials = {
    metal: new THREE.MeshStandardMaterial({color:0xc5d5df,metalness:.65,roughness:.4}),
    dark: new THREE.MeshStandardMaterial({color:0x263f50,metalness:.4,roughness:.55}),
    roll: new THREE.MeshStandardMaterial({color:0xef987b,metalness:.25,roughness:.45}),
    pitch: new THREE.MeshStandardMaterial({color:0x42cdbf,metalness:.4,roughness:.4}),
    yaw: new THREE.MeshStandardMaterial({color:0x6599db,metalness:.35,roughness:.4}),
    blade: new THREE.MeshStandardMaterial({color:0xe4f1f0,metalness:.25,roughness:.5}),
    ghost: new THREE.MeshBasicMaterial({color:0xffce83,wireframe:true,transparent:true,opacity:.45,depthWrite:false}),
  };
  type Mat = THREE.Material;
  function part(parent: THREE.Object3D, geometry: THREE.BufferGeometry, mat: Mat,
    size: [number,number,number], pos: [number,number,number]) {
    const mesh = new THREE.Mesh(geometry,mat); mesh.scale.set(...size); mesh.position.set(...pos); parent.add(mesh); return mesh;
  }
  function cyl(parent: THREE.Object3D, mat: Mat, radius:number, height:number, pos:[number,number,number], axis='z') {
    const mesh=part(parent,cylinder,mat,[radius,height,radius],pos);
    if(axis==='z')mesh.rotation.x=Math.PI/2;
    if(axis==='x')mesh.rotation.z=Math.PI/2;
    return mesh;
  }
  const fixed = new THREE.Group(); scene.add(fixed);
  part(fixed,box,materials.dark,[.63,.55,.09],[0,0,-.99]);
  cyl(fixed,materials.metal,.17,.08,[0,0,-.91]);
  cyl(fixed,materials.yaw,.055,.83,[0,0,-.455]);
  cyl(fixed,materials.metal,.087,.075,[0,0,-.067]);
  const bolts=new THREE.InstancedMesh(cylinder,materials.metal,4);
  const transform=new THREE.Object3D();let n=0;
  for(const x of [-.23,.23])for(const y of [-.19,.19]){
    transform.position.set(x,y,-.935);transform.rotation.x=Math.PI/2;transform.scale.set(.018,.018,.018);transform.updateMatrix();bolts.setMatrixAt(n++,transform.matrix);
  }
  fixed.add(bolts);
  const grid=new THREE.GridHelper(3.6,18,0x355c70,0x233e50);grid.rotation.x=Math.PI/2;grid.position.z=-1.045;scene.add(grid);
  function rig(ghost=false) {
    const yaw=new THREE.Group(),pitch=new THREE.Group(),roll=new THREE.Group();
    scene.add(yaw);yaw.add(pitch);pitch.add(roll);roll.position.x=1;
    const m=ghost?materials.ghost:materials.pitch;
    if(!ghost){
      cyl(yaw,materials.yaw,.105,.07,[0,0,-.015]);
      for(const y of [-.074,.074])part(yaw,box,materials.metal,[.075,.022,.17],[0,y,.035]);
      cyl(yaw,materials.pitch,.036,.21,[0,0,.07],'y');
    }
    part(pitch,box,m,[1.5,.045,.058],[.25,0,0]);
    cyl(pitch,ghost?m:materials.dark,.112,.19,[-.43,0,0],'x');
    if(!ghost){
      for(const x of [-.52,-.43,-.34])cyl(pitch,materials.metal,.115,.013,[x,0,0],'x');
      part(pitch,box,materials.dark,[.19,.13,.08],[.75,0,0]);
      cyl(pitch,materials.roll,.06,.12,[.94,0,0],'x');
    }
    part(roll,box,ghost?m:materials.roll,[.085,.66,.06],[0,0,0]);
    const rotors:THREE.Group[]=[];const details=new THREE.Group();roll.add(details);
    for(const y of [-.29,.29]){
      cyl(roll,ghost?m:materials.dark,.052,.10,[0,y,.035]);
      const rotor=new THREE.Group();rotor.position.set(0,y,.115);roll.add(rotor);rotors.push(rotor);
      part(rotor,box,ghost?m:materials.blade,[.35,.037,.009],[0,0,0]);
      if(!ghost){
        cyl(details,materials.metal,.055,.015,[0,y,.080]);
        cyl(rotor,materials.roll,.024,.025,[0,0,.006]);
        const ring=new THREE.Mesh(guard,materials.metal);ring.position.set(0,y,.11);details.add(ring);
        for(const sign of [-1,1])part(details,box,materials.dark,[.012,.17,.012],[0,y+sign*.10,.09]);
      }
    }
    return {yaw,pitch,roll,rotors,details};
  }
  const plant=rig(), estimate=rig(true);estimate.yaw.visible=false;
  return {plant,estimate,fixed,grid};
}

export function tipPosition(elevation:number,yaw:number) {
  return new THREE.Vector3(Math.cos(yaw)*Math.cos(elevation),Math.sin(yaw)*Math.cos(elevation),Math.sin(elevation));
}
