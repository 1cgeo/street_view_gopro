import * as THREE from 'three';

const IMAGES_LOCATION = "/IMG_CAMPO"
const METADATA_LOCATION = "/METADATA_CAMPO"
const queryString = window.location.search;
const urlParams = new URLSearchParams(queryString);

var camera, scene, renderer, offsetRad, material, mesh;
var nextTarget = null
var lastClickAt = null
var currentLookAt = null
var objects = []
var isUserInteracting = false,
    onPointerDownMouseX = 0, onPointerDownMouseY = 0,
    lon = 0, onPointerDownLon = 0,
    lat = 0, onPointerDownLat = 0,
    phi = 0, theta = 0;
var currentHoveElement = null
var raycaster = new THREE.Raycaster();
var mouse = new THREE.Vector2();
var currentPhotoName = ''
var imageName = urlParams.get('image')

var map = new maplibregl.Map({
    container: 'map',
    style: 'map-style.json',
    center: [-57.07505939012384, -29.78239512550811],
    zoom: 12.5
});

var miniMap2 = new maplibregl.Map({
    container: 'mini-map',
    style: 'map-style.json',
    center: [-57.07505939012384, -29.78239512550811],
    zoom: 12.5
});
$('#mini-map').css({
    display: 'none'
});

var photos = {}

if (imageName) {
    loadImageByName(imageName)
}

const setCurrentPhotoName = (name) => {
    currentPhotoName = name
    map.setFilter(
        'selected',
        [
            "all",
            [
                "==",
                "nome_img",
                currentPhotoName
            ]
        ],
    );
    miniMap2.setFilter(
        'selected',
        [
            "all",
            [
                "==",
                "nome_img",
                currentPhotoName
            ]
        ],
    );
    let found = photos.features.find(item => item.properties.nome_img == currentPhotoName)
    let long = found.geometry.coordinates[0]
    let lat = found.geometry.coordinates[1]
    miniMap2.setCenter([long, lat]);

}

const loadImageByName = (name) => {
    $.getJSON(`${METADATA_LOCATION}/${name}.json`, function (data) {
        init(data);
        animate();
    });
}

const setCurrentHoveElement = (name) => {
    currentHoveElement = name
    map.scrollZoom.enable();
    if (currentHoveElement != 'map') {
        map.scrollZoom.disable();
    }
}

module.setCurrentHoveElement = setCurrentHoveElement

const calculateTargetPositionInMeters = (
    cameraLocation,
    targetLocation
) => {
    const cameraLocationGeojson = turf.point([
        cameraLocation.longitude,
        cameraLocation.latitude
    ]);
    // x
    const xDest = {
        longitude: targetLocation.longitude,
        latitude: cameraLocation.latitude
    };

    const xDestGeojson = turf.point([xDest.longitude, xDest.latitude]);

    // TODO: turf??
    // let x = computeDistanceMeters(cameraLocation, xDest);
    let x = turf.distance(cameraLocationGeojson, xDestGeojson);
    x = x * 1000
    x *= targetLocation.longitude > cameraLocation.longitude ? 1 : -1;

    // console.log("x", x);
    // z
    const zDest = {
        longitude: cameraLocation.longitude,
        latitude: targetLocation.latitude
    };
    const zDestGeojson = turf.point([zDest.longitude, zDest.latitude]);

    // TODO: turf??
    // let z = computeDistanceMeters(cameraLocation, zDest);
    let z = turf.distance(cameraLocationGeojson, zDestGeojson);
    z = z * 1000
    z *= targetLocation.latitude > cameraLocation.latitude ? -1 : 1;



    // console.log("z", z);

    // console.log(targetLocation.latitude > cameraLocation.latitude);


    return [x, 0, z]; // [x, y, z]
};

const loadTarget = (name) => {
    for (let mesh of objects) {
        const object = scene.getObjectByProperty('uuid', mesh.uuid);
        object.geometry.dispose();
        object.material.dispose();
        scene.remove(object);
    }
    objects = []

    $.getJSON(`${METADATA_LOCATION}/${name}.json`, (data) => {
        const offset = data.camera.heading;
        offsetRad = THREE.MathUtils.degToRad(offset);
        setCurrentPhotoName(data.camera.img)
        let texture = new THREE.TextureLoader().load(
            `${IMAGES_LOCATION}/${data.camera.img}.webp`,
            (texture) => {
                material.map = texture
                mesh.rotation.y = offsetRad
                addCube(data);
                nextTarget = lastClickAt
            },
        );
    });

}

const addCube = (info) => {
    for (let target of info.targets) {
        const [x, y, z] = calculateTargetPositionInMeters(
            {
                latitude: info.camera.lat,
                longitude: info.camera.lon
            },
            {
                latitude: target.lat,
                longitude: target.lon
            }
        )
        //const geom = new THREE.CircleGeometry(0.5, 70);
        const geom = target.icon ? new THREE.PlaneGeometry(1.3, 1) : new THREE.CircleGeometry(0.5, 70);
        let texture = new THREE.TextureLoader().load(
            `${target.icon ? target.icon : "next"}.png`
        );
        let material = new THREE.MeshBasicMaterial({ map: texture, side: THREE.DoubleSide })
        material.transparent = true
        var mesh = new THREE.Mesh(geom, material);
        mesh.quaternion.copy(camera.quaternion);
        /* offsetRad = THREE.MathUtils.degToRad(-75);
        mesh.rotation.x = offsetRad */
        mesh.position.set(x, y, z);
        scene.add(mesh);

        mesh.callback = () => { loadTarget(target.id); }
        objects.push(mesh)
        if (!lastClickAt && target.next) {
            nextTarget = { x, y, z }
        }
    }
}

function init(info) {

    const container = document.getElementById('container');

    camera = new THREE.PerspectiveCamera(75, window.innerWidth / window.innerHeight, 0.1, 2000);
    //camera.rotation.reorder("YXZ");


    camera.position.set(0, -0.1, 0)

    scene = new THREE.Scene();

    const geometry = new THREE.SphereGeometry(500, 60, 40);
    // invert the geometry on the x-axis so that all of the faces point inward
    geometry.scale(- 1, 1, 1);
    setCurrentPhotoName(info.camera.img)
    let texture = new THREE.TextureLoader().load(
        `${IMAGES_LOCATION}/${info.camera.img}.webp`
    );

    material = new THREE.MeshBasicMaterial({ map: texture });
    mesh = new THREE.Mesh(geometry, material);
    mesh.name = 'MyObj_s';
    const offset = info.camera.heading;
    offsetRad = THREE.MathUtils.degToRad(offset);
    mesh.rotation.y = offsetRad
    scene.add(mesh);

    renderer = new THREE.WebGLRenderer();
    renderer.setPixelRatio(window.devicePixelRatio);
    renderer.setSize(window.innerWidth, window.innerHeight);
    container.appendChild(renderer.domElement);

    container.style.touchAction = 'none';
    container.addEventListener('pointerdown', onPointerDown);
    container.addEventListener('pointerdown', clickObj);

    document.addEventListener('wheel', onDocumentMouseWheel);

    //

    document.addEventListener('dragover', function (event) {

        event.preventDefault();
        event.dataTransfer.dropEffect = 'copy';

    });

    document.addEventListener('dragenter', function () {

        document.body.style.opacity = 0.5;

    });

    document.addEventListener('dragleave', function () {

        document.body.style.opacity = 1;

    });

    document.addEventListener('drop', function (event) {

        event.preventDefault();

        const reader = new FileReader();
        reader.addEventListener('load', function (event) {

            material.map.image.src = event.target.result;
            material.map.needsUpdate = true;

        });
        reader.readAsDataURL(event.dataTransfer.files[0]);

        document.body.style.opacity = 1;

    });

    //
    window.addEventListener('resize', onWindowResize);


    /////
    addCube(info)

}



function clickObj(event) {

    event.preventDefault();

    mouse.x = (event.clientX / renderer.domElement.clientWidth) * 2 - 1;
    mouse.y = - (event.clientY / renderer.domElement.clientHeight) * 2 + 1;

    raycaster.setFromCamera(mouse, camera);

    var intersects = raycaster.intersectObjects(objects);

    if (intersects.length > 0) {
        intersects[0].object.callback();

    }

}


function onWindowResize() {

    camera.aspect = window.innerWidth / window.innerHeight;
    camera.updateProjectionMatrix();

    renderer.setSize(window.innerWidth, window.innerHeight);

}

function onPointerDown(event) {
    if (event.isPrimary === false || nextTarget) return;

    isUserInteracting = true;

    onPointerDownMouseX = event.clientX;
    onPointerDownMouseY = event.clientY;

    onPointerDownLon = lon;
    onPointerDownLat = lat;

    mouse.x = event.clientX / window.innerWidth * 2 - 1;
    mouse.y = -(event.clientY / window.innerHeight) * 2 + 1;
    raycaster.setFromCamera(mouse, camera);
    var intersects = raycaster.intersectObjects([scene.getObjectByName('MyObj_s')], true);
    if (intersects.length > 0) {
        lastClickAt = intersects[0].point
    }
    document.addEventListener('pointermove', onPointerMove);
    document.addEventListener('pointerup', onPointerUp);

}

function onPointerMove(event) {

    if (event.isPrimary === false || !isUserInteracting) return;

    lon = (onPointerDownMouseX - event.clientX) * 0.1 + onPointerDownLon;
    lat = (event.clientY - onPointerDownMouseY) * 0.1 + onPointerDownLat;

    mouse.x = (onPointerDownMouseX - event.clientX) * 0.00005
    mouse.y = (event.clientY - onPointerDownMouseY) * 0.00005
    raycaster.setFromCamera(mouse, camera);
    var intersects = raycaster.intersectObjects([scene.getObjectByName('MyObj_s')], true);
    if (intersects.length > 0) {
        currentLookAt = intersects[0].point
    }

}

function onPointerUp() {

    if (event.isPrimary === false) return;

    isUserInteracting = false;

    document.removeEventListener('pointermove', onPointerMove);
    document.removeEventListener('pointerup', onPointerUp);

}

function onDocumentMouseWheel(event) {
    if (currentHoveElement != 'street') return
    const fov = camera.fov + event.deltaY * 0.05;

    camera.fov = THREE.MathUtils.clamp(fov, 10, 75);

    camera.updateProjectionMatrix();

}

function animate() {
    requestAnimationFrame(animate);
    update();
}

function update() {
    /* lat = Math.max(- 75, Math.min(75, lat));
    phi = THREE.MathUtils.degToRad(90 - lat);
    theta = THREE.MathUtils.degToRad(lon);
 
    const x = 2000 * Math.sin(phi) * Math.cos(theta);
    const y = 2000 * Math.cos(phi);
    const z = 2000 * Math.sin(phi) * Math.sin(theta); */
    if (nextTarget) {
        camera.lookAt(nextTarget.x, nextTarget.y, nextTarget.z);
        nextTarget = null
    } else if (currentLookAt) {
        camera.lookAt(currentLookAt.x, currentLookAt.y, currentLookAt.z);
        currentLookAt = null
    }
    objects.forEach(mesh => mesh.quaternion.copy(camera.quaternion))

    renderer.render(scene, camera);

}




map.on('mouseup', () => {
    console.log(map.getZoom())
    let bounds = map.getBounds()
    console.log([
        [bounds._sw.lng, bounds._sw.lat],
        [bounds._ne.lng, bounds._ne.lat]
    ])
    console.log(map.getCenter())
});

const setFullMap = (full) => {
    $('#map').css({
        display: full ? 'block' : 'none'
    });
    $('#mini-map').css({
        display: full ? 'none' : 'block'
    });
}

map.on('load', function () {
    $.getJSON("fotos.geojson", function (json) {
        photos = json
        map.loadImage(
            '/point.png',
            function (error, image) {
                if (error) throw error;
                map.addImage('point', image);

                map.addSource('points', {
                    'type': 'geojson',
                    'data': photos
                });

                map.addLayer({
                    'id': 'points',
                    'type': 'symbol',
                    'source': 'points',
                    'layout': {
                        'icon-image': 'point'
                    }
                });

                map.on('click', 'points', function (e) {
                    setFullMap(false)
                    if (scene) {
                        loadTarget(e.features[0].properties.nome_img)
                        return
                    }

                    loadImageByName(e.features[0].properties.nome_img)

                });

                map.on('mouseenter', 'points', function () {
                    map.getCanvas().style.cursor = 'pointer';
                });

                map.on('mouseleave', 'points', function () {
                    map.getCanvas().style.cursor = '';
                });
            }
        );

        map.loadImage(
            '/point-selected.png',
            function (error, image) {
                map.addImage('point-selected', image);
                map.addSource('selected', {
                    'type': 'geojson',
                    'data': photos
                });
                map.addLayer({
                    'id': 'selected',
                    'type': 'symbol',
                    'source': 'selected',
                    "filter": [
                        "all",
                        [
                            "==",
                            "nome_img",
                            currentPhotoName
                        ]
                    ],
                    'layout': {
                        'icon-image': 'point-selected'
                    }
                });
            }
        )
    });



});

miniMap2.on('load', function () {
    $.getJSON("fotos.geojson", function (json) {
        photos = json
        miniMap2.loadImage(
            '/point.png',
            function (error, image) {
                if (error) throw error;
                miniMap2.addImage('point', image);

                miniMap2.addSource('points', {
                    'type': 'geojson',
                    'data': photos
                });

                miniMap2.addLayer({
                    'id': 'points',
                    'type': 'symbol',
                    'source': 'points',
                    'layout': {
                        'icon-image': 'point'
                    }
                });

                miniMap2.on('click', 'points', function (e) {
                    if (scene) {
                        loadTarget(e.features[0].properties.nome_img)
                        return
                    }

                    loadImageByName(e.features[0].properties.nome_img)

                });

                miniMap2.on('mouseenter', 'points', function () {
                    miniMap2.getCanvas().style.cursor = 'pointer';
                });

                miniMap2.on('mouseleave', 'points', function () {
                    miniMap2.getCanvas().style.cursor = '';
                });
            }
        );

        miniMap2.loadImage(
            '/point-selected.png',
            function (error, image) {
                miniMap2.addImage('point-selected', image);
                miniMap2.addSource('selected', {
                    'type': 'geojson',
                    'data': photos
                });
                miniMap2.addLayer({
                    'id': 'selected',
                    'type': 'symbol',
                    'source': 'selected',
                    "filter": [
                        "all",
                        [
                            "==",
                            "nome_img",
                            currentPhotoName
                        ]
                    ],
                    'layout': {
                        'icon-image': 'point-selected'
                    }
                });
            }
        )
    });



});


$('.float-element').on("click", function () {
    var btnId = $(this).attr('id');
    let handle = {
        'open-full-map': () => setFullMap(true),
        'close-full-map': () => setFullMap(false)
    }
    handle[btnId]()
});