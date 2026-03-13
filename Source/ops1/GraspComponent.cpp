#include "GraspComponent.h"
#include "GameFramework/Actor.h"
#include "DrawDebugHelpers.h"

UGraspComponent::UGraspComponent()
{
    PrimaryComponentTick.bCanEverTick = true;
}

void UGraspComponent::BeginPlay()
{
    Super::BeginPlay();
    SetSphereRadius(15.0f);
    SetCollisionProfileName(TEXT("OverlapAllDynamic"));
    OnComponentBeginOverlap.AddDynamic(this, &UGraspComponent::OnOverlapBegin);
}

void UGraspComponent::TickComponent(float DeltaTime, ELevelTick TickType,
                                     FActorComponentTickFunction* ThisTickFunction)
{
    Super::TickComponent(DeltaTime, TickType, ThisTickFunction);

    if (GraspState == EGraspState::Idle ||
        GraspState == EGraspState::Complete ||
        GraspState == EGraspState::Failed)
        return;

    CycleTimeElapsed += DeltaTime;

    if (CycleTimeElapsed >= MaxCycleTimeSeconds)
    {
        FailWith(EFailureTag::Timeout);
        return;
    }

    if (GraspState == EGraspState::Carrying)
    {
        if (GraspedActor)
        {
            GraspedActor->SetActorLocation(GetComponentLocation(), false, nullptr, ETeleportType::TeleportPhysics);

            float Dist = FVector::Dist(GraspedActor->GetActorLocation(), GetComponentLocation());
            if (Dist > SphereRadius * 2.5f)
            {
                FailWith(EFailureTag::DropInTransit);
                return;
            }
        }

        float DistToTarget = FVector::Dist(GetComponentLocation(), TargetLocation);
        if (DistToTarget < 5.0f)
        {
            AttemptPlace();
        }
    }

    DrawDebugSphere(GetWorld(), GetComponentLocation(), SphereRadius, 12, FColor::Green, false, -1.0f);
    if (GraspState == EGraspState::Carrying)
    {
        DrawDebugLine(GetWorld(), GetComponentLocation(), TargetLocation, FColor::Yellow, false, -1.0f);
    }
}

void UGraspComponent::BeginGraspSequence(AActor* TargetObject, FVector PlacementTarget)
{
    if (!TargetObject) return;

    GraspedActor = nullptr;
    TargetLocation = PlacementTarget;
    FailureTag = EFailureTag::None;
    CycleTimeElapsed = 0.0f;
    PlacementErrorMM = 0.0f;
    GraspState = EGraspState::Reaching;

    AttemptGrasp();
}

void UGraspComponent::AttemptGrasp()
{
    TArray<AActor*> OverlappingActors;
    GetOverlappingActors(OverlappingActors);

    for (AActor* Actor : OverlappingActors)
    {
        if (Actor == GetOwner()) continue;

        UPrimitiveComponent* Prim = Cast<UPrimitiveComponent>(Actor->GetRootComponent());
        if (Prim && Prim->IsSimulatingPhysics())
        {
            Prim->SetSimulatePhysics(false);
            GraspedActor = Actor;
            GraspState = EGraspState::Carrying;
            return;
        }
    }

    FailWith(EFailureTag::GraspFail);
}

void UGraspComponent::AttemptPlace()
{
    if (!GraspedActor)
    {
        FailWith(EFailureTag::GraspFail);
        return;
    }

    UPrimitiveComponent* Prim = Cast<UPrimitiveComponent>(GraspedActor->GetRootComponent());
    if (Prim)
    {
        GraspedActor->SetActorLocation(TargetLocation, false, nullptr, ETeleportType::TeleportPhysics);
        Prim->SetSimulatePhysics(true);
    }

    PlacementErrorMM = FVector::Dist(GraspedActor->GetActorLocation(), TargetLocation) * 10.0f;

    if (PlacementErrorMM <= PlacementToleranceMM)
    {
        GraspState = EGraspState::Complete;
    }
    else
    {
        FailWith(EFailureTag::PlacementMiss);
    }

    GraspedActor = nullptr;
}

void UGraspComponent::FailWith(EFailureTag Tag)
{
    FailureTag = Tag;
    GraspState = EGraspState::Failed;

    if (GraspedActor)
    {
        UPrimitiveComponent* Prim = Cast<UPrimitiveComponent>(GraspedActor->GetRootComponent());
        if (Prim) Prim->SetSimulatePhysics(true);
        GraspedActor = nullptr;
    }
}

void UGraspComponent::ResetState()
{
    GraspState = EGraspState::Idle;
    FailureTag = EFailureTag::None;
    CycleTimeElapsed = 0.0f;
    PlacementErrorMM = 0.0f;
    GraspedActor = nullptr;
}

bool UGraspComponent::IsSequenceComplete() const
{
    return GraspState == EGraspState::Complete || GraspState == EGraspState::Failed;
}

bool UGraspComponent::WasSuccessful() const
{
    return GraspState == EGraspState::Complete;
}

void UGraspComponent::OnOverlapBegin(UPrimitiveComponent* OverlappedComp, AActor* OtherActor,
                                      UPrimitiveComponent* OtherComp, int32 OtherBodyIndex,
                                      bool bFromSweep, const FHitResult& SweepResult)
{
}