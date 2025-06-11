$begin 'Profile'
	$begin 'ProfileGroup'
		MajorVer=2024
		MinorVer=1
		Name='Solution Process'
		$begin 'StartInfo'
			I(1, 'Start Time', '06/11/2025 09:09:21')
			I(1, 'Host', 'RF01')
			I(1, 'Processor', '12')
			I(1, 'OS', 'NT 10.0')
			I(1, 'Product', 'HFSS Version 2024.1.0')
		$end 'StartInfo'
		$begin 'TotalInfo'
			I(1, 'Elapsed Time', '00:00:40')
			I(1, 'ComEngine Memory', '104 M')
		$end 'TotalInfo'
		GroupOptions=8
		TaskDataOptions('CPU Time'=8, Memory=8, 'Real Time'=8)
		ProfileItem('', 0, 0, 0, 0, 0, 'I(1, 1, \'Executing From\', \'C:\\\\Program Files\\\\AnsysEM\\\\v241\\\\v241\\\\Win64\\\\HFSSCOMENGINE.exe\')', false, true)
		$begin 'ProfileGroup'
			MajorVer=2024
			MinorVer=1
			Name='HPC'
			$begin 'StartInfo'
				I(1, 'Type', 'Auto')
				I(1, 'MPI Vendor', 'Intel')
				I(1, 'MPI Version', '2018')
			$end 'StartInfo'
			$begin 'TotalInfo'
				I(0, ' ')
			$end 'TotalInfo'
			GroupOptions=0
			TaskDataOptions(Memory=8)
			ProfileItem('Machine', 0, 0, 0, 0, 0, 'I(5, 1, \'Name\', \'RF01\', 1, \'Memory\', \'39.7 GB\', 3, \'RAM Limit\', 90, \'%f%%\', 2, \'Cores\', 20, false, 1, \'Free Disk Space\', \'254 GB\')', false, true)
		$end 'ProfileGroup'
		ProfileItem('', 0, 0, 0, 0, 0, 'I(1, 1, \'Allow off core\', \'True\')', false, true)
		ProfileItem('', 0, 0, 0, 0, 0, 'I(1, 1, \'Solution Basis Order\', \'1\')', false, true)
		ProfileItem('Design Validation', 0, 0, 0, 0, 0, 'I(1, 0, \'Elapsed time : 00:00:00 , HFSS ComEngine Memory : 99 M\')', false, true)
		ProfileItem('', 0, 0, 0, 0, 0, 'I(1, 0, \'Perform full validations with standard port validations\')', false, true)
		ProfileItem('', 0, 0, 0, 0, 0, 'I(1, 0, \'\')', false, true)
		$begin 'ProfileGroup'
			MajorVer=2024
			MinorVer=1
			Name='Initial Meshing'
			$begin 'StartInfo'
				I(1, 'Time', '06/11/2025 09:09:21')
			$end 'StartInfo'
			$begin 'TotalInfo'
				I(1, 'Elapsed Time', '00:00:09')
			$end 'TotalInfo'
			GroupOptions=4
			TaskDataOptions('CPU Time'=8, Memory=8, 'Real Time'=8)
			ProfileItem('Mesh', 4, 0, 5, 0, 151000, 'I(3, 1, \'Type\', \'TAU\', 2, \'Cores\', 20, false, 2, \'Tetrahedra\', 40394, false)', true, true)
			ProfileItem('Coarsen', 1, 0, 1, 0, 151000, 'I(1, 2, \'Tetrahedra\', 28959, false)', true, true)
			ProfileItem('Lambda Refine', 0, 0, 0, 0, 54604, 'I(2, 2, \'Tetrahedra\', 28959, false, 2, \'Cores\', 1, false)', true, true)
			ProfileItem('Simulation Setup', 0, 0, 0, 0, 249228, 'I(1, 1, \'Disk\', \'0 Bytes\')', true, true)
			ProfileItem('Port Adapt', 2, 0, 2, 0, 265472, 'I(2, 2, \'Tetrahedra\', 18750, false, 1, \'Disk\', \'333 KB\')', true, true)
			ProfileItem('Port Refine', 0, 0, 0, 0, 63044, 'I(2, 2, \'Tetrahedra\', 29722, false, 2, \'Cores\', 1, false)', true, true)
		$end 'ProfileGroup'
		$begin 'ProfileGroup'
			MajorVer=2024
			MinorVer=1
			Name='Adaptive Meshing'
			$begin 'StartInfo'
				I(1, 'Time', '06/11/2025 09:09:31')
			$end 'StartInfo'
			$begin 'TotalInfo'
				I(1, 'Elapsed Time', '00:00:09')
			$end 'TotalInfo'
			GroupOptions=4
			TaskDataOptions('CPU Time'=8, Memory=8, 'Real Time'=8)
			$begin 'ProfileGroup'
				MajorVer=2024
				MinorVer=1
				Name='Adaptive Pass 1'
				$begin 'StartInfo'
					I(1, 'Frequency', '1GHz')
				$end 'StartInfo'
				$begin 'TotalInfo'
					I(0, ' ')
				$end 'TotalInfo'
				GroupOptions=0
				TaskDataOptions('CPU Time'=8, Memory=8, 'Real Time'=8)
				ProfileItem(' ', 0, 0, 0, 0, 0, 'I(1, 0, \'\')', false, true)
				ProfileItem('Simulation Setup ', 0, 0, 0, 0, 259264, 'I(2, 2, \'Tetrahedra\', 19382, false, 1, \'Disk\', \'12.4 KB\')', true, true)
				ProfileItem('Matrix Assembly', 0, 0, 1, 0, 314056, 'I(10, 2, \'Tetrahedra\', 19382, false, 2, \'P1 Triangles\', 101, false, 2, \'P2 Triangles\', 92, false, 2, \'P3 Triangles\', 102, false, 2, \'P4 Triangles\', 95, false, 2, \'P5 Triangles\', 108, false, 2, \'P6 Triangles\', 88, false, 2, \'P7 Triangles\', 95, false, 2, \'P8 Triangles\', 99, false, 1, \'Disk\', \'0 Bytes\')', true, true)
				ProfileItem('Matrix Solve', 0, 0, 1, 0, 397684, 'I(5, 1, \'Type\', \'DRS\', 2, \'Cores\', 20, false, 2, \'Matrix size\', 92614, false, 3, \'Matrix bandwidth\', 14.6273, \'%5.1f\', 1, \'Disk\', \'1.64 KB\')', true, true)
				ProfileItem('Field Recovery', 0, 0, 1, 0, 397684, 'I(2, 2, \'Excitations\', 8, false, 1, \'Disk\', \'2.33 MB\')', true, true)
				ProfileItem('Data Transfer', 0, 0, 0, 0, 104024, 'I(1, 0, \'Adaptive Pass 1\')', true, true)
			$end 'ProfileGroup'
			ProfileItem('', 0, 0, 0, 0, 0, 'I(1, 0, \'\')', false, true)
			$begin 'ProfileGroup'
				MajorVer=2024
				MinorVer=1
				Name='Adaptive Pass 2'
				$begin 'StartInfo'
					I(1, 'Frequency', '1GHz')
				$end 'StartInfo'
				$begin 'TotalInfo'
					I(0, ' ')
				$end 'TotalInfo'
				GroupOptions=0
				TaskDataOptions('CPU Time'=8, Memory=8, 'Real Time'=8)
				ProfileItem('Adaptive Refine', 0, 0, 0, 0, 71348, 'I(2, 2, \'Tetrahedra\', 35538, false, 2, \'Cores\', 1, false)', true, true)
				ProfileItem(' ', 0, 0, 0, 0, 0, 'I(1, 0, \'\')', false, true)
				ProfileItem('Simulation Setup ', 0, 0, 0, 0, 276700, 'I(2, 2, \'Tetrahedra\', 24839, false, 1, \'Disk\', \'15.9 KB\')', true, true)
				ProfileItem('Matrix Assembly', 1, 0, 1, 0, 350068, 'I(10, 2, \'Tetrahedra\', 24839, false, 2, \'P1 Triangles\', 101, false, 2, \'P2 Triangles\', 92, false, 2, \'P3 Triangles\', 102, false, 2, \'P4 Triangles\', 95, false, 2, \'P5 Triangles\', 108, false, 2, \'P6 Triangles\', 88, false, 2, \'P7 Triangles\', 95, false, 2, \'P8 Triangles\', 99, false, 1, \'Disk\', \'6 Bytes\')', true, true)
				ProfileItem('Matrix Solve', 0, 0, 2, 0, 463812, 'I(5, 1, \'Type\', \'DRS\', 2, \'Cores\', 20, false, 2, \'Matrix size\', 122310, false, 3, \'Matrix bandwidth\', 15.3645, \'%5.1f\', 1, \'Disk\', \'2 Bytes\')', true, true)
				ProfileItem('Field Recovery', 0, 0, 2, 0, 463824, 'I(2, 2, \'Excitations\', 8, false, 1, \'Disk\', \'1.01 MB\')', true, true)
				ProfileItem('Data Transfer', 0, 0, 0, 0, 104268, 'I(1, 0, \'Adaptive Pass 2\')', true, true)
				ProfileItem('', 0, 0, 0, 0, 0, 'I(1, 3, \'Max Mag. Delta S\', 0.0059054, \'%.5f\')', false, true)
			$end 'ProfileGroup'
			ProfileFootnote('I(1, 0, \'Adaptive Passes converged\')', 0)
		$end 'ProfileGroup'
		$begin 'ProfileGroup'
			MajorVer=2024
			MinorVer=1
			Name='Frequency Sweep'
			$begin 'StartInfo'
				I(1, 'Time', '06/11/2025 09:09:41')
			$end 'StartInfo'
			$begin 'TotalInfo'
				I(1, 'Elapsed Time', '00:00:20')
			$end 'TotalInfo'
			GroupOptions=4
			TaskDataOptions('CPU Time'=8, Memory=8, 'Real Time'=8)
			ProfileItem('', 0, 0, 0, 0, 0, 'I(1, 1, \'HPC\', \'Enabled\')', false, true)
			ProfileItem('', 0, 0, 0, 0, 0, 'I(1, 0, \'\')', false, true)
			ProfileItem('Solution Sweep1', 0, 0, 0, 0, 0, 'I(1, 0, \'Fast Sweep\')', false, true)
			ProfileItem('', 0, 0, 0, 0, 0, 'I(1, 0, \'From 0.8 GHz to 1.2 GHz, 200 Steps\')', false, true)
			ProfileItem('Simulation Setup', 0, 0, 0, 0, 268556, 'I(1, 1, \'Disk\', \'0 Bytes\')', true, true)
			ProfileItem('Matrix Assembly', 1, 0, 1, 0, 352192, 'I(10, 2, \'Tetrahedra\', 24839, false, 2, \'P1 Triangles\', 101, false, 2, \'P2 Triangles\', 92, false, 2, \'P3 Triangles\', 102, false, 2, \'P4 Triangles\', 95, false, 2, \'P5 Triangles\', 108, false, 2, \'P6 Triangles\', 88, false, 2, \'P7 Triangles\', 95, false, 2, \'P8 Triangles\', 99, false, 1, \'Disk\', \'0 Bytes\')', true, true)
			ProfileItem('Matrix Solve', 18, 0, 21, 0, 626912, 'I(6, 1, \'Type\', \'DRS\', 2, \'Cores\', 20, false, 2, \'Matrix size\', 122310, false, 3, \'Matrix bandwidth\', 15.3645, \'%5.1f\', 2, \'Reduced matrix size\', 32, false, 1, \'Disk\', \'59.8 MB\')', true, true)
			ProfileItem('Field Recovery', 0, 0, 0, 0, 626912, 'I(2, 2, \'Excitations\', 8, false, 1, \'Disk\', \'0 Bytes\')', true, true)
		$end 'ProfileGroup'
		ProfileItem('', 0, 0, 0, 0, 0, 'I(1, 0, \'\')', false, true)
		$begin 'ProfileGroup'
			MajorVer=2024
			MinorVer=1
			Name='Simulation Summary'
			$begin 'StartInfo'
			$end 'StartInfo'
			$begin 'TotalInfo'
				I(0, ' ')
			$end 'TotalInfo'
			GroupOptions=0
			TaskDataOptions('CPU Time'=8, Memory=8, 'Real Time'=8)
			ProfileItem('Design Validation', 0, 0, 0, 0, 0, 'I(2, 1, \'Elapsed Time\', \'00:00:00\', 1, \'Total Memory\', \'99 MB\')', false, true)
			ProfileItem('Initial Meshing', 0, 0, 0, 0, 0, 'I(2, 1, \'Elapsed Time\', \'00:00:09\', 1, \'Total Memory\', \'407 MB\')', false, true)
			ProfileItem('Adaptive Meshing', 0, 0, 0, 0, 0, 'I(5, 1, \'Elapsed Time\', \'00:00:09\', 1, \'Average memory/process\', \'453 MB\', 1, \'Max memory/process\', \'453 MB\', 2, \'Max number of processes/frequency\', 1, false, 2, \'Total number of cores\', 20, false)', false, true)
			ProfileItem('Frequency Sweep', 0, 0, 0, 0, 0, 'I(2, 1, \'Elapsed Time\', \'00:00:20\', 1, \'Total Memory\', \'612 MB\')', false, true)
			ProfileFootnote('I(3, 2, \'Max solved tets\', 24839, false, 2, \'Max matrix size\', 122310, false, 1, \'Matrix bandwidth\', \'15.4\')', 0)
		$end 'ProfileGroup'
		ProfileFootnote('I(2, 1, \'Stop Time\', \'06/11/2025 09:10:01\', 1, \'Status\', \'Normal Completion\')', 0)
	$end 'ProfileGroup'
$end 'Profile'
