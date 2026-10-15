package bullet;

import cpp.Star;
import cpp.Reference;

// Value types (copied on the C++ stack)
@:buildXml('
<files id="haxe">
	<compilerflag value="-I/usr/include/bullet"/>
</files>
<target id="haxe">
	<lib name="-lBulletDynamics"/>
	<lib name="-lBulletCollision"/>
	<lib name="-lLinearMath"/>
</target>
')
@:include("btBulletDynamicsCommon.h")
@:native("btVector3") @:structAccess @:unreflective
extern class Vector3 {
	function new(x:Float, y:Float, z:Float);
	function setValue(x:Float, y:Float, z:Float):Void;
	function x():Float;
	function y():Float;
	function z():Float;
}

@:include("btBulletDynamicsCommon.h")
@:native("btQuaternion") @:structAccess @:unreflective
extern class Quaternion {
	function x():Float;
	function y():Float;
	function z():Float;
	function w():Float;
}

@:include("btBulletDynamicsCommon.h")
@:native("btTransform") @:structAccess @:unreflective
extern class Transform {
	function new();
	function setIdentity():Void;
	function setOrigin(v:Vector3):Void;
	function getOrigin():Vector3;
	function getRotation():Quaternion;
}

// Heap types (created with "new", handled as pointers)
@:include("btBulletDynamicsCommon.h")
@:native("btDefaultCollisionConfiguration") @:structAccess @:unreflective
extern class DefaultCollisionConfiguration {
	@:native("new btDefaultCollisionConfiguration") static function create():Star<DefaultCollisionConfiguration>;
}

@:include("btBulletDynamicsCommon.h")
@:native("btCollisionDispatcher") @:structAccess @:unreflective
extern class CollisionDispatcher {
	@:native("new btCollisionDispatcher") static function create(c:Star<DefaultCollisionConfiguration>):Star<CollisionDispatcher>;
}

@:include("btBulletDynamicsCommon.h")
@:native("btDbvtBroadphase") @:structAccess @:unreflective
extern class DbvtBroadphase {
	@:native("new btDbvtBroadphase") static function create():Star<DbvtBroadphase>;
}

@:include("btBulletDynamicsCommon.h")
@:native("btSequentialImpulseConstraintSolver") @:structAccess @:unreflective
extern class SequentialImpulseConstraintSolver {
	@:native("new btSequentialImpulseConstraintSolver") static function create():Star<SequentialImpulseConstraintSolver>;
}

@:include("btBulletDynamicsCommon.h")
@:native("btCollisionShape") @:structAccess @:unreflective
extern class CollisionShape {
}

@:include("btBulletDynamicsCommon.h")
@:native("btStaticPlaneShape") @:structAccess @:unreflective
extern class StaticPlaneShape extends CollisionShape {
	@:native("new btStaticPlaneShape") static function create(normal:Vector3, c:Float):Star<StaticPlaneShape>;
}

@:include("btBulletDynamicsCommon.h")
@:native("btBoxShape") @:structAccess @:unreflective
extern class BoxShape extends CollisionShape {
	@:native("new btBoxShape") static function create(halfExtents:Vector3):Star<BoxShape>;
	function getHalfExtentsWithMargin():Vector3;
}

@:include("btBulletDynamicsCommon.h")
@:native("btMotionState") @:structAccess @:unreflective
extern class MotionState {
	function getWorldTransform(t:Reference<Transform>):Void;
}

@:include("btBulletDynamicsCommon.h")
@:native("btDefaultMotionState") @:structAccess @:unreflective
extern class DefaultMotionState extends MotionState {
	@:native("new btDefaultMotionState") static function create(start:Transform, offset:Transform):Star<DefaultMotionState>;
}

@:include("btBulletDynamicsCommon.h")
@:native("btRigidBody::btRigidBodyConstructionInfo") @:structAccess @:unreflective
extern class RigidBodyConstructionInfo {
	@:native("new btRigidBody::btRigidBodyConstructionInfo")
	static function create(mass:Float, ms:Star<DefaultMotionState>, shape:Star<CollisionShape>, inertia:Vector3):Star<RigidBodyConstructionInfo>;
}

@:include("btBulletDynamicsCommon.h")
@:native("btRigidBody") @:structAccess @:unreflective
extern class RigidBody {
	@:native("new btRigidBody")
	static function create(mass:Float, ms:Star<DefaultMotionState>, shape:Star<CollisionShape>, inertia:Vector3):Star<RigidBody>;
	function setDamping(lin:Float, ang:Float):Void;
	function setFriction(f:Float):Void;
	function setRestitution(r:Float):Void;
	function getMotionState():Star<MotionState>;
}

@:include("btBulletDynamicsCommon.h")
@:native("btDiscreteDynamicsWorld") @:structAccess @:unreflective
extern class DiscreteDynamicsWorld {
	@:native("new btDiscreteDynamicsWorld")
	static function create(d:Star<CollisionDispatcher>, b:Star<DbvtBroadphase>, s:Star<SequentialImpulseConstraintSolver>, c:Star<DefaultCollisionConfiguration>):Star<DiscreteDynamicsWorld>;
	function setGravity(g:Vector3):Void;
	function addRigidBody(b:Star<RigidBody>):Void;
	function stepSimulation(dt:Float, ?maxSub:Int, ?fixed:Float):Int;
}
