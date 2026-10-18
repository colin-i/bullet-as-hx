package;

#if cpp
import cpp.Reference;
#end

// Generated from Clang AST. Review translated bodies before using in production.
#if cpp
@:nativeGen
@:structAccess
#end
class BoxShape
{
	var halfExtents:bullet.Bt.Vector3;
	public function new(halfExtents:bullet.Bt.Vector3)
	{
		this.halfExtents = halfExtents;
	}
	function getHalfExtentsWithMargin():bullet.Bt.Vector3
	{
		return halfExtents;
	}
	public function calculateLocalInertia(mass:Float, inertia:#if cpp Reference<bullet.Bt.Vector3> #else bullet.Bt.Vector3 #end):Void
	{
		var halfExtents:bullet.Bt.Vector3 = this.getHalfExtentsWithMargin();
		var lx:Float = (2 * halfExtents.x());
		var ly:Float = (2 * halfExtents.y());
		var lz:Float = (2 * halfExtents.z());
		inertia.setValue(((mass / 12) * ((ly * ly) + (lz * lz))), ((mass / 12) * ((lx * lx) + (lz * lz))), ((mass / 12) * ((lx * lx) + (ly * ly))));
	}

}
