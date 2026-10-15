package;

import openfl.display.Sprite;
import openfl.events.Event;
import openfl.geom.Matrix3D;
import openfl.geom.Vector3D;
import openfl.Vector;

import away3d.containers.View3D;
import away3d.entities.Mesh;
import away3d.materials.ColorMaterial;
import away3d.primitives.CubeGeometry;
import away3d.primitives.PlaneGeometry;

/**
 * Simplest Away3D + Bullet test: a red cube falls onto a grey floor.
 * Bullet position and rotation are copied to the Away3D mesh.
 */
class Main extends Sprite
{
	// 1 Bullet unit = 100 Away3D units (Bullet likes objects around 0.1..10 units)
	static inline var SCALE:Float = 100;
	// wait a moment before starting the simulation so you can see the fall
	static inline var START_DELAY:Int = 90;

	var view:View3D;
	var cube:Mesh;

	var world:cpp.Star<bullet.Bt.DiscreteDynamicsWorld>;
	var cubeBody:cpp.Star<bullet.Bt.RigidBody>;
	var tmp:bullet.Bt.Transform = new bullet.Bt.Transform();
	var cubeMatrix:Matrix3D = new Matrix3D();
	var raw:Vector<Float> = new Vector<Float>(16);
	var frames:Int = 0;

	public function new()
	{
		super();

		// ---------- Away3D ----------
		view = new View3D();
		addChild(view);

		var floor = new Mesh(new PlaneGeometry(2000, 2000), new ColorMaterial(0x888888));
		view.scene.addChild(floor); // plane lies at y = 0

		cube = new Mesh(new CubeGeometry(SCALE, SCALE, SCALE), new ColorMaterial(0xff0000));
		cube.y = 5 * SCALE;
		view.scene.addChild(cube);

		view.camera.z = -1200;
		view.camera.y = 400;
		view.camera.lookAt(new Vector3D(0, 150, 0));

		// ---------- Bullet ----------
		#if js
		// Modern ammo.js initialises asynchronously: Ammo() returns a promise that
		// resolves to the module holding btDefaultCollisionConfiguration etc.
		// Put that module back on window.Ammo, where the haxebullet externs look.
		js.Syntax.code("Ammo()").then(function(module:Dynamic) {
			js.Syntax.code("window.Ammo = {0}", module);
			initBullet();
		});
		#else
		initBullet();
		#end

		addEventListener(Event.ENTER_FRAME, onEnterFrame);
	}

	function initBullet():Void
	{
		var config = bullet.Bt.DefaultCollisionConfiguration.create();
		var dispatcher = bullet.Bt.CollisionDispatcher.create(config);
		var broadphase = bullet.Bt.DbvtBroadphase.create();
		var solver = bullet.Bt.SequentialImpulseConstraintSolver.create();
		world = bullet.Bt.DiscreteDynamicsWorld.create(dispatcher, broadphase, solver, config);
		world.setGravity(new bullet.Bt.Vector3(0, -9.81, 0));

		var groundShape = bullet.Bt.StaticPlaneShape.create(new bullet.Bt.Vector3(0, 1, 0), 0);
		var id = new bullet.Bt.Transform();
		id.setIdentity();
		var groundMotion = bullet.Bt.DefaultMotionState.create(id, id);
		world.addRigidBody(bullet.Bt.RigidBody.create(0, groundMotion, cast groundShape, new bullet.Bt.Vector3(0, 0, 0)));

		var boxShape = bullet.Bt.BoxShape.create(new bullet.Bt.Vector3(0.5, 0.5, 0.5));
		var a=new A();a.setHalfExtents(new bullet.Bt.Vector3(0.5, 0.5, 0.5));

		var boxTransform = new bullet.Bt.Transform();
		boxTransform.setIdentity();
		boxTransform.setOrigin(new bullet.Bt.Vector3(0, 5, 0));
		var boxMotion = bullet.Bt.DefaultMotionState.create(boxTransform, id);
		var inertia = new bullet.Bt.Vector3(0, 0, 0);

		//boxShape.calculateLocalInertia(1, inertia);
		a.calculateLocalInertia(1, inertia);

		cubeBody = bullet.Bt.RigidBody.create(1, boxMotion, cast boxShape, inertia);
		cubeBody.setDamping(0.02, 0.7);
		cubeBody.setFriction(0.8);
		cubeBody.setRestitution(0);
		world.addRigidBody(cubeBody);

		syncCube();
	}

	// Keep the rendered mesh aligned with the rigid body's full pose.
	function syncCube():Void
	{
		cubeBody.getMotionState().getWorldTransform(tmp);
		var o = tmp.getOrigin();
		var q = tmp.getRotation();
		var x:Float = q.x();
		var y:Float = q.y();
		var z:Float = q.z();
		var w:Float = q.w();

		raw[0]  = 1 - 2 * (y * y + z * z);
		raw[1]  = 2 * (x * y + z * w);
		raw[2]  = 2 * (x * z - y * w);
		raw[3]  = 0;
		raw[4]  = 2 * (x * y - z * w);
		raw[5]  = 1 - 2 * (x * x + z * z);
		raw[6]  = 2 * (y * z + x * w);
		raw[7]  = 0;
		raw[8]  = 2 * (x * z + y * w);
		raw[9]  = 2 * (y * z - x * w);
		raw[10] = 1 - 2 * (x * x + y * y);
		raw[11] = 0;
		raw[12] = o.x() * SCALE;
		raw[13] = o.y() * SCALE;
		raw[14] = o.z() * SCALE;
		raw[15] = 1;

		cubeMatrix.copyRawDataFrom(raw);
		cube.transform = cubeMatrix;
	}

	function onEnterFrame(event:Event):Void
	{
		frames++;

		if (world != null)
		{
			if (frames > START_DELAY) world.stepSimulation(1 / 60);
			syncCube();

			if (frames % 30 == 0) trace("cube y (bullet units): " + tmp.getOrigin().y());
		}

		view.render();
	}
}
