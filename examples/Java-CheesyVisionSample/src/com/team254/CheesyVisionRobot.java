/*----------------------------------------------------------------------------*/
/* Copyright (c) FIRST 2008. All Rights Reserved.                             */
/* Open Source Software - may be modified and shared by FRC teams. The code   */
/* must be accompanied by the FIRST BSD license file in the root directory of */
/* the project.                                                               */
/*----------------------------------------------------------------------------*/

package com.team254;


import com.team254.lib.CheesyVisionServer;
import edu.wpi.first.wpilibj.IterativeRobot;

/**
 * @author Tom Bottiglieri
 * Team 254, The Cheesy Poofs
 */
public class CheesyVisionRobot extends IterativeRobot {

    CheesyVisionServer server = CheesyVisionServer.getInstance();
    public final int listenPort = 1180;
    
    public void robotInit() {
        server.setPort(listenPort);
        server.start();
    }

    public void autonomousInit() {
        server.reset();
        server.startSamplingCounts();
    }
    
    public void disabledInit() {
        server.stopSamplingCounts();
    }
    

    public void autonomousPeriodic() {
        System.out.println("Current left: " + server.getLeftStatus() + ", current right: " + server.getRightStatus());
        System.out.println("Left count: " + server.getLeftCount() + ", right count: " + server.getRightCount() + ", total: " + server.getTotalCount() + "\n");
    }
}
