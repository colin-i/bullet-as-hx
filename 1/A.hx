import cpp.Reference;

@:nativeGen
@:structAccess
class A
{
	var halfExtents:bullet.Bt.Vector3;

	public function new(halfExtents:bullet.Bt.Vector3) {
		this.halfExtents = halfExtents;
	}

	function getHalfExtentsWithMargin():bullet.Bt.Vector3
	{
		return halfExtents;
	}

	public function calculateLocalInertia(
		mass:Float,
		inertia:Reference<bullet.Bt.Vector3>
	):Void
	{
		var halfExtents = getHalfExtentsWithMargin();
		var lx = 2 * halfExtents.x();
		var ly = 2 * halfExtents.y();
		var lz = 2 * halfExtents.z();

		inertia.setValue(
			mass / 12 * (ly * ly + lz * lz),
			mass / 12 * (lx * lx + lz * lz),
			mass / 12 * (lx * lx + ly * ly)
		);
	}
}
