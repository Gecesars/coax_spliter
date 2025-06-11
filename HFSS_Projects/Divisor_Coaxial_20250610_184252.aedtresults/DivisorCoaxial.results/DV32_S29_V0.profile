$begin 'Profile'
	$begin 'ProfileGroup'
		MajorVer=2024
		MinorVer=1
		Name='Solution Process'
		$begin 'StartInfo'
			I(1, 'Start Time', '06/10/2025 18:43:58')
			I(1, 'Host', 'RF01')
			I(1, 'Processor', '12')
			I(1, 'OS', 'NT 10.0')
			I(1, 'Product', 'HFSS Version 2024.1.0')
		$end 'StartInfo'
		$begin 'TotalInfo'
			I(1, 'Elapsed Time', '00:00:58')
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
			ProfileItem('Machine', 0, 0, 0, 0, 0, 'I(5, 1, \'Name\', \'RF01\', 1, \'Memory\', \'39.7 GB\', 3, \'RAM Limit\', 90, \'%f%%\', 2, \'Cores\', 20, false, 1, \'Free Disk Space\', \'255 GB\')', false, true)
		$end 'ProfileGroup'
		ProfileItem('', 0, 0, 0, 0, 0, 'I(1, 1, \'Allow off core\', \'True\')', false, true)
		ProfileItem('', 0, 0, 0, 0, 0, 'I(1, 1, \'Solution Basis Order\', \'1\')', false, true)
		ProfileItem('Design Validation', 0, 0, 0, 0, 0, 'I(1, 0, \'Elapsed time : 00:00:00 , HFSS ComEngine Memory : 98.3 M\')', false, true)
		ProfileItem('', 0, 0, 0, 0, 0, 'I(1, 0, \'Perform full validations with standard port validations\')', false, true)
		ProfileItem('', 0, 0, 0, 0, 0, 'I(1, 0, \'\')', false, true)
		$begin 'ProfileGroup'
			MajorVer=2024
			MinorVer=1
			Name='Initial Meshing'
			$begin 'StartInfo'
				I(1, 'Time', '06/10/2025 18:43:58')
			$end 'StartInfo'
			$begin 'TotalInfo'
				I(1, 'Elapsed Time', '00:00:06')
			$end 'TotalInfo'
			GroupOptions=4
			TaskDataOptions('CPU Time'=8, Memory=8, 'Real Time'=8)
			ProfileItem('Mesh', 2, 0, 2, 0, 89000, 'I(3, 1, \'Type\', \'TAU\', 2, \'Cores\', 20, false, 2, \'Tetrahedra\', 23459, false)', true, true)
			ProfileItem('Coarsen', 1, 0, 1, 0, 89000, 'I(1, 2, \'Tetrahedra\', 16650, false)', true, true)
			ProfileItem('Lambda Refine', 0, 0, 0, 0, 38316, 'I(2, 2, \'Tetrahedra\', 16650, false, 2, \'Cores\', 1, false)', true, true)
			ProfileItem('Simulation Setup', 0, 0, 0, 0, 217548, 'I(1, 1, \'Disk\', \'0 Bytes\')', true, true)
			ProfileItem('Port Adapt', 1, 0, 1, 0, 229756, 'I(2, 2, \'Tetrahedra\', 11005, false, 1, \'Disk\', \'210 KB\')', true, true)
			ProfileItem('Port Refine', 0, 0, 0, 0, 44988, 'I(2, 2, \'Tetrahedra\', 17188, false, 2, \'Cores\', 1, false)', true, true)
		$end 'ProfileGroup'
		$begin 'ProfileGroup'
			MajorVer=2024
			MinorVer=1
			Name='Adaptive Meshing'
			$begin 'StartInfo'
				I(1, 'Time', '06/10/2025 18:44:05')
			$end 'StartInfo'
			$begin 'TotalInfo'
				I(1, 'Elapsed Time', '00:00:05')
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
				ProfileItem('Simulation Setup ', 0, 0, 0, 0, 222840, 'I(2, 2, \'Tetrahedra\', 11487, false, 1, \'Disk\', \'6.88 KB\')', true, true)
				ProfileItem('Matrix Assembly', 0, 0, 0, 0, 260632, 'I(7, 2, \'Tetrahedra\', 11487, false, 2, \'P1 Triangles\', 103, false, 2, \'P2 Triangles\', 98, false, 2, \'P3 Triangles\', 99, false, 2, \'P4 Triangles\', 103, false, 2, \'P5 Triangles\', 104, false, 1, \'Disk\', \'0 Bytes\')', true, true)
				ProfileItem('Matrix Solve', 0, 0, 0, 0, 311196, 'I(5, 1, \'Type\', \'DRS\', 2, \'Cores\', 20, false, 2, \'Matrix size\', 55127, false, 3, \'Matrix bandwidth\', 14.8107, \'%5.1f\', 1, \'Disk\', \'1.64 KB\')', true, true)
				ProfileItem('Field Recovery', 0, 0, 0, 0, 311196, 'I(2, 2, \'Excitations\', 5, false, 1, \'Disk\', \'1.37 MB\')', true, true)
				ProfileItem('Data Transfer', 0, 0, 0, 0, 103496, 'I(1, 0, \'Adaptive Pass 1\')', true, true)
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
				ProfileItem('Adaptive Refine', 0, 0, 0, 0, 49084, 'I(2, 2, \'Tetrahedra\', 20635, false, 2, \'Cores\', 1, false)', true, true)
				ProfileItem(' ', 0, 0, 0, 0, 0, 'I(1, 0, \'\')', false, true)
				ProfileItem('Simulation Setup ', 0, 0, 0, 0, 231988, 'I(2, 2, \'Tetrahedra\', 14665, false, 1, \'Disk\', \'10.8 KB\')', true, true)
				ProfileItem('Matrix Assembly', 0, 0, 1, 0, 279196, 'I(7, 2, \'Tetrahedra\', 14665, false, 2, \'P1 Triangles\', 103, false, 2, \'P2 Triangles\', 98, false, 2, \'P3 Triangles\', 99, false, 2, \'P4 Triangles\', 103, false, 2, \'P5 Triangles\', 104, false, 1, \'Disk\', \'0 Bytes\')', true, true)
				ProfileItem('Matrix Solve', 0, 0, 1, 0, 344272, 'I(5, 1, \'Type\', \'DRS\', 2, \'Cores\', 20, false, 2, \'Matrix size\', 72337, false, 3, \'Matrix bandwidth\', 15.4485, \'%5.1f\', 1, \'Disk\', \'0 Bytes\')', true, true)
				ProfileItem('Field Recovery', 0, 0, 0, 0, 344272, 'I(2, 2, \'Excitations\', 5, false, 1, \'Disk\', \'601 KB\')', true, true)
				ProfileItem('Data Transfer', 0, 0, 0, 0, 103672, 'I(1, 0, \'Adaptive Pass 2\')', true, true)
				ProfileItem('', 0, 0, 0, 0, 0, 'I(1, 3, \'Max Mag. Delta S\', 0.00610803, \'%.5f\')', false, true)
			$end 'ProfileGroup'
			ProfileFootnote('I(1, 0, \'Adaptive Passes converged\')', 0)
		$end 'ProfileGroup'
		$begin 'ProfileGroup'
			MajorVer=2024
			MinorVer=1
			Name='Frequency Sweep'
			$begin 'StartInfo'
				I(1, 'Time', '06/10/2025 18:44:11')
			$end 'StartInfo'
			$begin 'TotalInfo'
				I(1, 'Elapsed Time', '00:00:46')
			$end 'TotalInfo'
			GroupOptions=4
			TaskDataOptions('CPU Time'=8, Memory=8, 'Real Time'=8)
			ProfileItem('', 0, 0, 0, 0, 0, 'I(1, 1, \'HPC\', \'Enabled\')', false, true)
			ProfileItem('', 0, 0, 0, 0, 0, 'I(1, 0, \'\')', false, true)
			ProfileItem('Solution Sweep_HKTJP9', 0, 0, 0, 0, 0, 'I(1, 0, \'Fast Sweep\')', false, true)
			ProfileItem('', 0, 0, 0, 0, 0, 'I(1, 0, \'From 2.5 GHz to 7.5 GHz, 400 Steps\')', false, true)
			ProfileItem('Simulation Setup', 0, 0, 0, 0, 226292, 'I(1, 1, \'Disk\', \'0 Bytes\')', true, true)
			ProfileItem('Matrix Assembly', 0, 0, 0, 0, 279176, 'I(7, 2, \'Tetrahedra\', 14665, false, 2, \'P1 Triangles\', 103, false, 2, \'P2 Triangles\', 98, false, 2, \'P3 Triangles\', 99, false, 2, \'P4 Triangles\', 103, false, 2, \'P5 Triangles\', 104, false, 1, \'Disk\', \'0 Bytes\')', true, true)
			ProfileItem('Matrix Solve', 44, 0, 45, 0, 470828, 'I(6, 1, \'Type\', \'DRS\', 2, \'Cores\', 20, false, 2, \'Matrix size\', 72337, false, 3, \'Matrix bandwidth\', 15.4485, \'%5.1f\', 2, \'Reduced matrix size\', 60, false, 1, \'Disk\', \'67.8 MB\')', true, true)
			ProfileItem('Field Recovery', 0, 0, 0, 0, 470828, 'I(2, 2, \'Excitations\', 5, false, 1, \'Disk\', \'0 Bytes\')', true, true)
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
			ProfileItem('Design Validation', 0, 0, 0, 0, 0, 'I(2, 1, \'Elapsed Time\', \'00:00:00\', 1, \'Total Memory\', \'98.3 MB\')', false, true)
			ProfileItem('Initial Meshing', 0, 0, 0, 0, 0, 'I(2, 1, \'Elapsed Time\', \'00:00:06\', 1, \'Total Memory\', \'311 MB\')', false, true)
			ProfileItem('Adaptive Meshing', 0, 0, 0, 0, 0, 'I(5, 1, \'Elapsed Time\', \'00:00:05\', 1, \'Average memory/process\', \'336 MB\', 1, \'Max memory/process\', \'336 MB\', 2, \'Max number of processes/frequency\', 1, false, 2, \'Total number of cores\', 20, false)', false, true)
			ProfileItem('Frequency Sweep', 0, 0, 0, 0, 0, 'I(2, 1, \'Elapsed Time\', \'00:00:46\', 1, \'Total Memory\', \'460 MB\')', false, true)
			ProfileFootnote('I(3, 2, \'Max solved tets\', 14665, false, 2, \'Max matrix size\', 72337, false, 1, \'Matrix bandwidth\', \'15.4\')', 0)
		$end 'ProfileGroup'
		ProfileFootnote('I(2, 1, \'Stop Time\', \'06/10/2025 18:44:57\', 1, \'Status\', \'Normal Completion\')', 0)
	$end 'ProfileGroup'
$end 'Profile'
