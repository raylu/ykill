import ctypes

class LibDogma:
	OK = 0
	STATE_Online     = 0b00010001
	STATE_Active     = 0b00011111
	STATE_Overloaded = 0b00111111

	def __init__(self):
		self.libdogma = ctypes.CDLL('dogma/libdogma.so')
		self.init()

	def __getattr__(self, name):
		def check_call(*args):
			r = func(*args)
			if r != self.OK:
				raise RuntimeError('{} returned {}'.format(name, r))

		func = getattr(self.libdogma, 'dogma_' + name)
		return check_call

dgm = LibDogma()

class Dogma:
	hp_types = {
		'shield': 263, # ATT_ShieldCapacity
		'armor':  265, # ATT_ArmorHP
		'hull':   9,   # ATT_Hp
	}
	resists = {
		'shield': {
			'em':        271, # ATT_ShieldEmDamageResonance
			'thermal':   274, # ATT_ShieldThermalDamageResonance
			'kinetic':   273, # ATT_ShieldKineticDamageResonance
			'explosive': 272, # ATT_ShieldExplosiveDamageResonance
		},
		'armor': {
			'em':        267, # ATT_ArmorEmDamageResonance
			'thermal':   270, # ATT_ArmorThermalDamageResonance
			'kinetic':   269, # ATT_ArmorKineticDamageResonance
			'explosive': 268, # ATT_ArmorExplosiveDamageResonance
		},
		'hull': {
			'em':        113, # ATT_EmDamageResonance
			'thermal':   110, # ATT_ThermalDamageResonance
			'kinetic':   109, # ATT_KineticDamageResonance
			'explosive': 111, # ATT_ExplosiveDamageResonance
		},
	}

	def __init__(self):
		void_star = ctypes.POINTER(ctypes.c_int)
		ctx = void_star()
		dgm.init_context(ctypes.pointer(ctx))
		dgm.set_default_skill_level(ctx, 5)

		self.ctx = ctx
		self.slots = []

	def set_ship(self, type_id):
		dgm.set_ship(self.ctx, type_id)

	def add_module(self, type_id):
		slot = ctypes.c_ulong()
		dgm.add_module(self.ctx, type_id, ctypes.pointer(slot))
		dgm.set_module_state(self.ctx, slot, dgm.STATE_Active)
		self.slots.append(slot)

	def overload(self):
		for slot in self.slots:
			dgm.set_module_state(self.ctx, slot, dgm.STATE_Overloaded)

	def get_attribute(self, attr):
		value = ctypes.c_double()
		dgm.get_ship_attribute(self.ctx, attr, ctypes.pointer(value))
		return value.value

	def __del__(self):
		dgm.free_context(self.ctx)
