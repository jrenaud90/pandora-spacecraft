KPL/FK


Pandora Spacecraft Frame Definitions Kernel
==============================================================================

   This frame kernel contains the Pandora spacecraft and science
   instrument definitions.


Version and Date
----------------------------------------------------------

   The TEXT_KERNEL_ID stores version information of loaded project text
   kernels. Each entry associated with the keyword is a string that
   consists of four parts: the kernel name, version, entry date, and
   type. For example, the Pandora Frame-kernel might have an entry as
   follows:

      TEXT_KERNEL_ID += 'PANDORA_FRAMES  V0.0.1 11-JULY-2024 FK'
                             |             |         |        |
                             |             |         |        |
         KERNEL NAME <-------+             |         |        |
                                           |         |        V
                           VERSION <-------+         |   KERNEL TYPE
                                                     |
                                                     V
                                                ENTRY DATE

    Version 0.0.1 -- July 11, 2024 -- Andrew Gardner.

       -  Initial pass at a frame kernel for Pandora.

    Version 0.0.2 -- August 22, 2024 -- Andrew Gardner.

       -  Additional parameters specified, remove unnecessary dynamic frame.

    Version 0.0.3 -- August 28, 2024 -- Andrew Gardner

       -  Additional notes on the expected changes in the future.

    Version 0.0.4 -- September 17, 2024 -- Andrew Gardner.
       -  Changes based on closer reading of [5].

    Version 0.0.5 -- January 23, 2025 -- Andrew Gardner.
       -  Correct mistakes and add tests.

    Version 0.0.6 -- January 27, 2025 -- Andrew Gardner.
       -  Correct text, add shield.

    Version 0.0.10 -- March 16, 2026 -- Andrew Gardner. 
       -  Re-align the instrument to the body frame.

   Pandora Frame Kernel Version:

      \begindata

         TEXT_KERNEL_ID += 'PANDORA_FRAMES V0.0.10 16-MARCH-2026 FK'

      \begintext

References
----------------------------------------------------------

   1.   ``C-kernel Required Reading''
        https://naif.jpl.nasa.gov/pub/naif/toolkit_docs/C/req/ck.html

   2.   ``Kernel Pool Required Reading''
        https://naif.jpl.nasa.gov/pub/naif/toolkit_docs/C/req/kernel.html

   3.   ``Frames Required Reading''
        https://naif.jpl.nasa.gov/pub/naif/toolkit_docs/C/req/frames.html

   4.   ``NAIF IDs''
        https://naif.jpl.nasa.gov/pub/naif/toolkit_docs/C/req/naif_ids.html#Spacecraft

   4.   Pandora Bus-Payload Mechanical Interface Control
        Document 138MICD0001 rev A.

   5.   Pandora Spacecraft Configuration Document, Rev A, 138SCD0001.


Contact Information
----------------------------------------------------------

   Direct questions, comments, or concerns about the contents of this kernel
   to:

      Andrew Gardner, agardner@arizona.edu, 520-626-5496, 520-275-2148


Implementation Notes
----------------------------------------------------------

   This file is used by the SPICE system as follows: programs that make
   use of this frame kernel must `load' the kernel, normally during
   program initialization. The SPICELIB routine FURNSH loads a kernel
   file as shown below (see [2]):

      FORTRAN: (SPICELIB)

         CALL FURNSH ( frame_kernel_name )

      C: (CSPICE)

         furnsh_c ( frame_kernel_name );

      IDL: (Icy)

         cspice_furnsh, frame_kernel_name

      MATLAB: (Mice)

         cspice_furnsh( frame_kernel_name )

   This file was created and may be updated with a text editor or word
   processor.

Notes
----------------------------------------------------------
   
   The Pandora spacecraft (PANDORA_SC) frame is defined in [4, 5] as follows:

   1.  The SC coordinate system is Cartesian and right-handed with
       its three axes mutually orthogonal.

   2.  The +X axis is normal to the side of the rectangular spacecraft 
       bus onto which the star trackers and +X S-band antenna are mounted.

   3.  The +Y axis is normal to the side of the spacecraft bus onto 
       which the single solar array is attached.

   4.  The +Z axis is normal to the X-Y plane and is aligned with the
       instrument boresight.

   This diagram illustrates the spacecraft bus coordinate frame:


               |---------|
               |    ^    |
               |    |    | <- Telescope
               |   +Z    |
               |         |
               -----------
          |-------------------|
          |                   |                  Solar array
          |        +X     +Y->|------------------------------
          |                   |
          |-------------------|

          +X is directed out of the screen towards the reader.

   The spacecraft bus is rectangular.

   On the +X face of the bus:
      - An S-band antenna.
      - The two star trackers. 
   
   On the -X face of the bus:
      - An S-band antenna.
      - The X-band antenna. 
      - The payload electronics.
      - FAU IMU and magnetometer.

   On the +Y face of the bus:
      - The solar array deployment assembly and the solar array itself.

   On the -Z face of the bus:
      - The launch adapter interface.
      - The GPS antenna.
      - The three sun sensors, which each have different orientations.
      - The origin of the spacecraft bus coordinate system, which
        is at the center of the launch adapter interface on the
        external face.


PANDORA NAIF ID Codes -- Definitions
----------------------------------------------------------

   This section contains names to NAIF ID mappings for the Pandora
   spacecraft and instruments. Once the contents of this file is 
   loaded into the KERNEL POOL, these mappings become available 
   within SPICE, making it possible to use names instead of
   ID codes in the high level SPICE routine calls.

   PANDORA is the spacecraft's integer identifier, currently 
   the temporary NORAD ID. In keeping with NAIF practice, the
   spacecraft's integer identifier is the negative of the NORAD code.

   PANDORA_SC is the spacecraft body frame.

   PANDORA_X_BEAM is the path of the X-band antenna.

   PANDORA_INSTR is the instrument boresight.

   PANDORA_NST1 is the boresight of star tracker 1.

   PANDORA_NST2 is the boresight of star tracker 2.

   PANDORA_SHIELD is the face of the thermal shield.

       \begindata

          NAIF_BODY_NAME += ( 'PANDORA'                 )
          NAIF_BODY_CODE += ( -99152                    )

          NAIF_BODY_NAME += ( 'PANDORA_SC'              )
          NAIF_BODY_CODE += ( -9915200                  )

          NAIF_BODY_NAME += ( 'PANDORA_INSTR'           )
          NAIF_BODY_CODE += ( -9915210                  )

          NAIF_BODY_NAME += ( 'PANDORA_X_BEAM'          )
          NAIF_BODY_CODE += ( -9915220                  )

          NAIF_BODY_NAME += ( 'PANDORA_SOLAR_ARRAY_ARM' )
          NAIF_BODY_CODE += ( -9915230                  )

          NAIF_BODY_NAME += ( 'PANDORA_SOLAR_ARRAY'     )
          NAIF_BODY_CODE += ( -9915231                  )

          NAIF_BODY_NAME += ( 'PANDORA_NST1'            )
          NAIF_BODY_CODE += ( -9915241                  )

          NAIF_BODY_NAME += ( 'PANDORA_NST2'            )
          NAIF_BODY_CODE += ( -9915242                  )

          NAIF_BODY_NAME += ( 'PANDORA_GPS'             )
          NAIF_BODY_CODE += ( -9915250                  )

          NAIF_BODY_NAME += ( 'PANDORA_SHIELD'          )
          NAIF_BODY_CODE += ( -9915260                  )

      \begintext

   Assumptions:
   
   A1: During vehicle integration, we will measure an offset between the 
   X-band antenna frame and the spacecraft body frame due to 
   mechanical tolerances.

   A2: During vehicle integration, we will measure an offset between the 
   instrument frame and the spacecraft body frame due to 
   mechanical tolerances.

   We do not need to track the vectors associated with the S-band
   antennas. When we are pointed specifically for a telcom pass, the
   X-band antenna will be pointed at the ground station; we assume
   that the S-band antenna that is also on the -X face of the bus
   is sufficiently aligned that we can count it the same as the 
   X-band. When the spacecraft is not pointed for telecom, the 
   two S-band antennas provide sufficient coverage that they can be
   signaled by a ground station, e.g., when the spacecraft is in 
   safe-mode.

Pandora Frames
----------------------------------------------------------

   The following Pandora frames are defined in this kernel file:

      Frame Name                Relative To             Type      Frame ID
      =======================   ===================     =======   ========

   Spacecraft Body Frame (-992520x):
   ----------------------
      PANDORA_SC                J2000                   CK        -9915200

   Instrument Frames (-991521x):
   ------------------------------
      PANDORA_INSTR             PANDORA_SC              FIXED     -9915210

   Star Tracker Frames (-991524x):
   ------------------------------
      PANDORA_NST1              PANDORA_SC              FIXED     -9915241
      PANDORA_NST2              PANDORA_SC              FIXED     -9915242

Pandora Frames Hierarchy
----------------------------------------------------------

   The diagram below shows the Pandora frames hierarchy:


        'ITRF93' (EARTH BODY FIXED)
         |
         | <--- pck
         |
        'J2000' INERTIAL
         |
         | <--- ck
         |
        'PANDORA_SC'___________________________________________________________________
                      |
                      | <--- fixed
                      |
                      'PANDORA_X_BEAM', 'PANDORA_INSTR', 'PANDORA_NSTx', 
                      'PANDORA_GPS', 'PANDORA_SOLAR_ARRAY_ARM', 'PANDORA_SHIELD'
                                      |
                                      | <--- ck
                                      |
                                      'PANDORA_SOLAR_ARRAY'


Spacecraft Frame (PANDORA_SC)
----------------------------------------------------------

   Because the spacecraft bus attitude with respect to an inertial
   frame is provided by a C kernel (see [1] for more information), the
   PANDORA_SC frame is defined as a CK-based frame.

      \begindata

         FRAME_PANDORA_SC         = -9915200
         FRAME_-9915200_NAME      = 'PANDORA_SC'
         FRAME_-9915200_CLASS     = 3
         FRAME_-9915200_CLASS_ID  = -9915200
         FRAME_-9915200_CENTER    = -99152
         CK_-9915200_SCLK         = -99152
         CK_-9915200_SPK          = -99152

      \begintext


Pandora Instrument Boresight Frame (PANDORA_INSTR)
----------------------------------------------------------

   As described in [4] and [5], the Pandora Instrument Boresight
   Frame (PANDORA_INSTR) points in the +Z direction relative to the 
   right-handed spacecraft frame.

   The frame integer code is the negative spacecraft ID with the suffix 100.
   The name of the frame is PANDORA_INSTR.
   The frame is a fixed rotation from the spacecraft frame, so it is Class 4.
   The class ID is the same as the frame ID because this is a TK (fixed) frame.
   The center of the frame it the center of the spacecraft reference frame.
   The frame will be specified with Euler angles relative to the spacecraft frame in degrees.

   PANDORA_INSTR is rotated with respect to the spacecraft body frame because the
   primary axis of the instrument is +Z and the best way to accomplish this
   transform is to rotate 90 degrees down in Y, making the Z axis take the place
   of the primary axix (in this case, just the first axis) of the spacecraft
   body frame.

      \begindata

         FRAME_PANDORA_INSTR        = -9915210
         FRAME_-9915210_NAME        = 'PANDORA_INSTR'
         FRAME_-9915210_CLASS       = 4
         FRAME_-9915210_CLASS_ID    = -9915210
         FRAME_-9915210_CENTER      = -99152
         TKFRAME_-9915210_SPEC      = 'ANGLES'
         TKFRAME_-9915210_RELATIVE  = 'PANDORA_SC'
         TKFRAME_-9915210_ANGLES    = (  0.0,    0.0,   0.0 )
         TKFRAME_-9915210_AXES      = (    1,      2,     3 )
         TKFRAME_-9915210_UNITS     = 'DEGREES'

      \begintext

Pandora Star Tracker Frames (PANDORA_{NST1,NST2})
----------------------------------------------------------

   As described in [4] and [5], two star trackers are fixed to the
   spacecraft bus pointing out of the +X face of the spacecraft bus at
   fixed rotations.
   
   The frame integer code is the negative spacecraft ID with the suffixes 401 and 402.
   The name of the frames is PANDORA_NST1 PANDORA_NST2.
   The frame is a fixed rotation from the spacecraft frame, so it is Class 4.
   The class ID is the same as the frame ID because this is a TK (fixed) frame.
   The center of the frame is the center of the spacecraft reference frame.
   The frame will be specified with rotation matrices relative to the spacecraft frame in degrees.

      \begindata

         FRAME_PANDORA_NST1           = -9915241
         FRAME_-9915241_NAME          = 'PANDORA_NST1'
         FRAME_-9915241_CLASS         = 4
         FRAME_-9915241_CLASS_ID      = -9915241
         FRAME_-9915241_CENTER        = -99152
         TKFRAME_-9915241_SPEC        = 'ANGLES'
         TKFRAME_-9915241_RELATIVE    = 'PANDORA_SC'
         TKFRAME_-9915241_ANGLES      = ( 31.9455, 42.8783, -45.89 )
         TKFRAME_-9915241_AXES        = ( 1, 2, 3 )
         TKFRAME_-9915241_UNITS       = 'DEGREES'

         FRAME_PANDORA_NST2           = -9915242
         FRAME_-9915242_NAME          = 'PANDORA_NST2'
         FRAME_-9915242_CLASS         = 4
         FRAME_-9915242_CLASS_ID      = -9915242
         FRAME_-9915242_CENTER        = -99152
         TKFRAME_-9915242_SPEC        = 'ANGLES'
         TKFRAME_-9915242_RELATIVE    = 'PANDORA_SC'
         TKFRAME_-9915242_ANGLES      = ( -31.9455, 42.8783, -45.89 )
         TKFRAME_-9915242_AXES        = ( 1, 2, 3 )
         TKFRAME_-9915242_UNITS       = 'DEGREES'

      \begintext
