#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "GraspComponent.h"
#include "RobotArm.generated.h"

UCLASS()
class OPS1_API ARobotArm : public AActor
{
    GENERATED_BODY()

public:
ARobotArm(const FObjectInitializer& ObjectInitializer);

    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "OptiSim")
    UGraspComponent* GraspComponent;

    UFUNCTION(BlueprintCallable, Category = "OptiSim")
    void ExecuteTrial(AActor* TargetObject, FVector PlacementTarget);

    UFUNCTION(BlueprintCallable, Category = "OptiSim")
    bool IsTrialComplete() const;

    UFUNCTION(BlueprintCallable, Category = "OptiSim")
    void ResetForNextTrial();

protected:
    virtual void BeginPlay() override;
    virtual void Tick(float DeltaTime) override;
};