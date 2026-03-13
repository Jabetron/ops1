#pragma once

#include "CoreMinimal.h"
#include "Components/SphereComponent.h"
#include "GraspComponent.generated.h"

UENUM(BlueprintType)
enum class EGraspState : uint8
{
    Idle,
    Reaching,
    Grasping,
    Carrying,
    Placing,
    Complete,
    Failed
};

UENUM(BlueprintType)
enum class EFailureTag : uint8
{
    None,
    GraspFail,
    PlacementMiss,
    Timeout,
    DropInTransit
};

UCLASS(ClassGroup=(Custom), meta=(BlueprintSpawnableComponent))
class OPS1_API UGraspComponent : public USphereComponent
{
    GENERATED_BODY()

public:
    UGraspComponent();

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "OptiSim|Config")
    float PlacementToleranceMM = 20.0f;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "OptiSim|Config")
    float MaxCycleTimeSeconds = 6.0f;

    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "OptiSim|State")
    EGraspState GraspState = EGraspState::Idle;

    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "OptiSim|State")
    EFailureTag FailureTag = EFailureTag::None;

    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "OptiSim|State")
    float CycleTimeElapsed = 0.0f;

    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "OptiSim|State")
    float PlacementErrorMM = 0.0f;

    UFUNCTION(BlueprintCallable, Category = "OptiSim")
    void BeginGraspSequence(AActor* TargetObject, FVector PlacementTarget);

    UFUNCTION(BlueprintCallable, Category = "OptiSim")
    bool IsSequenceComplete() const;

    UFUNCTION(BlueprintCallable, Category = "OptiSim")
    bool WasSuccessful() const;

    UFUNCTION(BlueprintCallable, Category = "OptiSim")
    void ResetState();

protected:
    virtual void BeginPlay() override;
    virtual void TickComponent(float DeltaTime, ELevelTick TickType,
                               FActorComponentTickFunction* ThisTickFunction) override;

private:
    UPROPERTY()
    AActor* GraspedActor = nullptr;

    FVector TargetLocation;

    void AttemptGrasp();
    void AttemptPlace();
    void FailWith(EFailureTag Tag);

    UFUNCTION()
    void OnOverlapBegin(UPrimitiveComponent* OverlappedComp, AActor* OtherActor,
                        UPrimitiveComponent* OtherComp, int32 OtherBodyIndex,
                        bool bFromSweep, const FHitResult& SweepResult);
};