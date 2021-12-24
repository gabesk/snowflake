void setup() {
    // anodes. NOTE: PORTC PIN7 is connected to VCC so can't set low
    PORTC = 0x00;
    DDRC = 0x3f;
    // cathodes.
    PORTD = 0xff;
    DDRD = 0xff;

  // from https://www.gammon.com.au/power: save power
  // disable ADC
  ADCSRA = 0;  

  // turn off various modules
  power_all_disable ();
}

// from https://www.avrfreaks.net/forum/very-fastsmall-random-number-generator?page=all
uint8_t rnd(void) {
    static uint8_t s = 0xaa, a = 0;

    s ^= s << 3;
    s ^= s >> 5;
    s ^= a++ >> 2;
    return s;
}

// from https://learn.adafruit.com/led-tricks-gamma-correction/the-quick-fix
const uint8_t gamma_tbl[] = {
    0,  0,  0,  0,  0,  0,  0,  0,  1,  1,  1,  2,  2,  3,  3,  4,
    5,  6,  7,  8,  9, 10, 12, 13, 15, 17, 19, 21, 23, 26, 28, 31 };

#define NUM_LEDS_IN_PARALLEL 2
/*
 * Each LED structure holds the information about one of ^ above number of
 * parallel LEDs that can be twinkling.
 * The anode and cathode variables are bitmasks, storing the bit of the pin
 * directly to speed up the PWM routine below.
 * Same with gamma_corrected, so it doesn't have to be looked up later.
 * 
 */
struct led {
    uint8_t anode, cathode;
    int8_t intensity;
    int8_t gamma_corrected;
    int8_t step_size;

    // Every time tick is called,
    void tick() {
        // see if this LED is currently twinkling.
        if (!step_size) {
            // If it's not, with some probability, start twinkling. (The mask 
            // can be increased to make it less likely that it will be 0, and
            // reduce the liklihood of starting a new twinkle, and similarly
            // with reducing it.
            if (!(rnd() & 0x0f)) {
                // If starting a new twinkle, pick a random LED (by picking an
                // anode and cathode). Note that due to the multiplexing of LEDs
                // on the spires of the snowflake, only one anode (corresponding
                // to one spire) can be turned on at a time without duplicate
                // LEDs. But, in practice, the duplicates seem to be visually
                // pleasing so no attempt is made to synchronize the multiple LEDs.
                intensity = 0;
                // Also, pick a random step size. This controls how fast the LED
                // twinkles off->on->off. This gives 4 possible speeds (1,2,4,8)
                // per step.
                step_size = 1 << (rnd() & 0x3);
                anode = 1 << (rnd() % 6);
                cathode = 1 << (rnd() % 8);
            }
        }
        // If LED wasn't chosen to start twinkling, bail out early.
        if (!step_size) return;

        // Ramp up or down the intensity,
        intensity = (intensity + step_size) & 0x1F;
        // and look up the gamma.
        gamma_corrected = gamma_tbl[intensity];

        // If the intensity is still something (not 0), we're done.
        if (intensity) return;
        // However, by virtue of choosing the step size above as a power of 2,
        // it will eventually wrap around to exactly 0 or count down to 0.
        if (step_size < 0) {
            // At that point, there are two possiblities. One is that we're
            // already counting down, in which case clear the step size to
            // indicate this LED isn't actively twinkling any longer and we're
            // done, until randomly chosen to start twinkling again.
            step_size = 0;
            return;
        }

        // Otherwise, flip the sign of the step to start counting down,
        step_size *= -1;
        // and do a final addition so it doesn't go through a zero step.
        intensity = (intensity + step_size) & 0x1F;
        gamma_corrected = gamma_tbl[intensity];
    }
};

struct led leds[NUM_LEDS_IN_PARALLEL] = { 0 };

// The AVR has hardware PWM timers, but there aren't enough of them to PWM every
// LED on the snowflake. (In practice, since we can only safely enable one spire
// and only want a few LEDs twinkling at once, we could have definitely gotten
// away with using the 5! PWM timers. Oh well, whatever. In any case, this
// routine does software PWM.
void pwm() {
  // All LEDs start in the on part of the PWM duty cycle,
  for (uint8_t i = 0; i < NUM_LEDS_IN_PARALLEL; i++) {
      // unless they're off the entire time, in which case don't cause a tiny
      // pulse blip.
      if (leds[i].gamma_corrected) {
          PORTC |= leds[i].anode;
          PORTD &= ~leds[i].cathode;
      }
  }

  // Now, ramp through all phases of the PWM duty cycle and turn off each LED
  // when the counter reaches the appropriate point.
  for (uint8_t i = 0; i < 32; i++) {
      for (uint8_t j = 0; j < NUM_LEDS_IN_PARALLEL; j++) {
          if (leds[j].gamma_corrected == i) {
              PORTC &= ~leds[j].anode;
              PORTD |= leds[j].cathode;
          }
      }
  }
}

// For ever and ever,
void loop() {
    // Step the parallel LED twinklers,
    for (uint8_t i = 0; i < NUM_LEDS_IN_PARALLEL; i++) leds[i].tick();
    // and then run the software PWM for however long we've emperically
    // determined is the right amount for nice visuals.
    uint8_t j = 12; // adjust to speed up or slow down the twinkles
    while (j--) pwm();
}
