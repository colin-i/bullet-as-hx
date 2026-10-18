// Generated from Clang AST. Translated method bodies are emitted where supported; remaining methods use stubs.
btBoxShape.prototype.calculateLocalInertia = function(mass, inertia) {
	var halfExtents = this.getHalfExtentsWithMargin();
	var lx = (2 * halfExtents.x());
	var ly = (2 * halfExtents.y());
	var lz = (2 * halfExtents.z());
	inertia.setValue(((mass / 12) * ((ly * ly) + (lz * lz))), ((mass / 12) * ((lx * lx) + (lz * lz))), ((mass / 12) * ((lx * lx) + (ly * ly))));
};
